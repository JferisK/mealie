from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from mealie.core.config import get_app_settings
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.db.models.users.users import User
from mealie.repos.repository_household_planner import RepositoryHouseholdPlanner, RevisionConflict
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household.group_shopping_list import ShoppingListAddRecipeParamsBulk
from mealie.schema.household_planner.models import (
    BatchIn,
    GoalRevision,
    GoalsIn,
    HealthSyncIn,
    IdeaIn,
    MovementIn,
    PersonalOut,
    PersonalState,
    PlanIn,
    PlannerState,
    PlanOut,
    ProfileIn,
    RecipeFactsIn,
    StateOut,
)
from mealie.services.household_planner.calculations import fresh_servings, monthly_proposal, plan_summary, reserved
from mealie.services.household_planner.service import PlannerService
from mealie.services.household_services.shopping_lists import ShoppingListService
from mealie.services.recipe.ingredient_rules import ingredient_problems

router = APIRouter(prefix="/households/planning", tags=["Households: Planning"])


@controller(router)
class HouseholdPlannerController(BaseUserController):
    def _repo(self, private: bool = False) -> RepositoryHouseholdPlanner:
        key = f"user:{self.user.id}" if private else f"household:{self.household_id}"
        return RepositoryHouseholdPlanner(self.session, key)

    def _service(self, revision: int | None = None) -> PlannerService:
        service = PlannerService(self._repo())
        # Deleted recipes vanish from every view; the cleaned state is stored with the next write.
        service.forget_recipes(self._deleted(service.recipe_ids()))
        if revision is not None:
            try:
                service.expect(revision)
            except RevisionConflict as exc:
                raise HTTPException(409, str(exc)) from exc
        return service

    def _deleted(self, recipe_ids: set[UUID]) -> set[UUID]:
        if not recipe_ids:
            return set()
        existing = self.session.scalars(
            select(RecipeModel.id).where(RecipeModel.group_id == self.group_id, RecipeModel.id.in_(recipe_ids))
        )
        return recipe_ids - set(existing)

    def _without_deleted(self, data: PlanIn) -> PlanIn:
        """A page opened before a recipe was deleted may still send it; those entries are dropped."""
        gone = self._deleted({e.recipe_id for e in data.entries})
        return data.model_copy(update={"entries": [e for e in data.entries if e.recipe_id not in gone]})

    def _members(self) -> set[UUID]:
        return {u.id for u in self.session.query(User).filter(User.household_id == self.household_id).all()}

    def _write(self, service: PlannerService) -> StateOut:
        try:
            service.save()
        except RevisionConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        return StateOut(revision=service.revision, state=self._live(service.state))

    def _live(self, state: PlannerState) -> PlannerState:
        """Name, slug and image always come from the recipe as it is now; the planner only keeps copies."""
        out = state.model_copy(deep=True)
        copies = [
            *out.facts.values(),
            *(b.facts for b in out.batches.values()),
            *(f for p in out.plans.values() for f in p.recipe_snapshots.values()),
            *out.ideas.values(),
        ]
        ids = {c.recipe_id for c in copies}
        if not ids:
            return out
        rows = (
            self.session.query(RecipeModel.id, RecipeModel.name, RecipeModel.slug, RecipeModel.image)
            .filter(RecipeModel.group_id == self.group_id, RecipeModel.id.in_(ids))
            .all()
        )
        live = {row.id: row for row in rows}
        for copy in copies:
            if row := live.get(copy.recipe_id):
                copy.name, copy.slug, copy.image = row.name, row.slug, row.image
        return out

    def _sync_shopping(self, plan: PlanOut | None, before: PlanOut | None) -> None:
        """Bring the linked native list in line with the week's fresh cooking (adds/removes the difference).

        Only the difference to what was transferred earlier is applied, so manual +/- on the list survive.
        """
        link = plan or before
        if not link or not link.shopping_list_id:
            return
        list_id = link.shopping_list_id
        added = before.shopping_servings if before and before.shopping_list_id == list_id else {}
        target = fresh_servings(plan) if plan else {}
        if not self.repos.group_shopping_lists.get_one(list_id):
            if plan:  # list was deleted: drop the link silently
                plan.shopping_list_id, plan.shopping_servings = None, {}
            return
        changes: list[tuple[UUID, float, float]] = []  # recipe, delta servings, recipe yield
        for recipe_id in dict.fromkeys([*added, *target]):
            delta = target.get(recipe_id, 0) - added.get(recipe_id, 0)
            if abs(delta) < 1e-9:
                continue
            recipe = self.repos.recipes.get_one(UUID(recipe_id), key="id")
            if not recipe:
                continue
            if not recipe.recipe_servings or recipe.recipe_servings <= 0:
                raise HTTPException(422, f"{recipe.name}: Bitte im Rezept die Anzahl der Portionen eintragen.")
            changes.append((recipe.id, delta, recipe.recipe_servings))
        service = ShoppingListService(self.repos)
        for recipe_uuid, delta, yield_ in changes:
            if delta < 0:
                # a dish dropped to zero removes its whole share, despite float rounding of earlier steps
                gone = target.get(str(recipe_uuid), 0) <= 0
                service.remove_recipe_ingredients_from_list(
                    list_id, recipe_uuid, -delta / yield_ + (1e-6 if gone else 0)
                )
        additions = [
            ShoppingListAddRecipeParamsBulk(recipe_id=r, recipe_increment_quantity=d / y)
            for r, d, y in changes
            if d > 0
        ]
        if additions:
            service.add_recipe_ingredients_to_list(list_id, additions)
        if plan:
            plan.shopping_list_id, plan.shopping_servings = list_id, target

    def _check_plan(self, service: PlannerService, data: PlanIn) -> dict:
        try:
            summary = service.validate_plan(data, self._members())
            for e in data.entries:
                facts = (
                    service.state.batches[str(e.batch_id)].facts
                    if e.batch_id
                    else service.state.facts[str(e.recipe_id)]
                )
                _, payload = RepositoryHouseholdPlanner(self.session, f"user:{e.user_id}").read()
                profile = PersonalState.model_validate(payload).profile
                if profile.gluten_free and facts.gluten_free != "yes":
                    raise ValueError("A recipe is not verified suitable for an assigned person's gluten restriction")
                if profile.lactose_free and facts.lactose_free != "yes":
                    raise ValueError("A recipe is not verified suitable for an assigned person's lactose restriction")
                if profile.avoid_traces:
                    raise ValueError(
                        "Strict trace avoidance requires individual review; automated plan confirmation is unavailable"
                    )
            return summary
        except (ValueError, KeyError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("", response_model=StateOut)
    def get_state(self):
        s = self._service()
        return StateOut(revision=s.revision, state=self._live(s.state))

    @router.get("/members")
    def members(self):
        result = []
        for user in self.session.query(User).filter(User.household_id == self.household_id).all():
            _, payload = RepositoryHouseholdPlanner(self.session, f"user:{user.id}").read()
            profile = PersonalState.model_validate(payload).profile
            result.append(
                {
                    "id": str(user.id),
                    "name": user.full_name or user.username,
                    "meal_preferences": {
                        "gluten_free": profile.gluten_free,
                        "lactose_free": profile.lactose_free,
                        "avoid_traces": profile.avoid_traces,
                        "dislikes": profile.dislikes,
                    },
                }
            )
        return result

    @router.put("/recipe-facts", response_model=StateOut)
    def recipe_facts(self, data: RecipeFactsIn, revision: int = Query(ge=0)):
        s = self._service(revision)
        recipe = self.repos.recipes.get_one(data.recipe_id, key="id")
        if not recipe or recipe.household_id != self.household_id:
            raise HTTPException(404, "Recipe not found in this household")
        if get_app_settings().STRICT_INGREDIENTS and (problems := ingredient_problems(recipe.recipe_ingredient)):
            raise HTTPException(422, "Rezept zuerst mit Mengen und Lebensmitteln parsen: " + "; ".join(problems))
        if (data.gluten_free == "yes" or data.lactose_free == "yes") and not data.evidence.strip():
            raise HTTPException(422, "Verified dietary suitability requires evidence")
        s.facts(data, recipe.name, recipe.slug, recipe.image)
        s.mirror_native_nutrition(data.recipe_id)
        return self._write(s)

    @router.post("/preview")
    def preview(self, data: PlanIn):
        data = self._without_deleted(data)
        s = self._service()
        return {"revision": s.revision, "plan": data, "summary": self._check_plan(s, data)}

    @router.post("/confirm", response_model=StateOut)
    def confirm(self, data: PlanIn, revision: int = Query(ge=0)):
        data = self._without_deleted(data)
        s = self._service(revision)
        if str(data.id) not in s.state.plans:
            self._check_plan(s, data)
        before = s.week_plan(data.start)
        before = before.model_copy(deep=True) if before else None
        try:
            s.confirm(data, self._members(), self.group_id, self.user.id)
            self._sync_shopping(s.week_plan(data.start), before)
            return self._write(s)
        except ValueError as exc:
            self.session.rollback()
            raise HTTPException(422, str(exc)) from exc

    @router.put("/weeks/{start}", response_model=StateOut)
    def save_week(self, start: date, data: PlanIn, revision: int = Query(ge=0)):
        if data.start != start:
            raise HTTPException(422, "Week start does not match the URL")
        data = self._without_deleted(data)
        s = self._service(revision)
        if data.entries:
            self._check_plan(s, data)
        before = s.week_plan(start)
        before = before.model_copy(deep=True) if before else None
        try:
            s.save_week(data, self._members(), self.group_id, self.user.id)
            self._sync_shopping(s.week_plan(start), before)
            return self._write(s)
        except ValueError as exc:
            self.session.rollback()
            raise HTTPException(422, str(exc)) from exc

    @router.post("/ideas", response_model=StateOut)
    def add_idea(self, data: IdeaIn, revision: int = Query(ge=0)):
        s = self._service(revision)
        recipe = self.repos.recipes.get_one(data.recipe_id, key="id")
        if not recipe or recipe.household_id != self.household_id:
            raise HTTPException(404, "Recipe not found in this household")
        try:
            s.add_idea(data, recipe.name, recipe.slug, self.user.id)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return self._write(s)

    @router.post("/ideas/{idea_id}/like", response_model=StateOut)
    def like_idea(self, idea_id: UUID, revision: int = Query(ge=0)):
        s = self._service(revision)
        try:
            s.toggle_like(idea_id, self.user.id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return self._write(s)

    @router.delete("/ideas/{idea_id}", response_model=StateOut)
    def remove_idea(self, idea_id: UUID, revision: int = Query(ge=0)):
        s = self._service(revision)
        try:
            s.remove_idea(idea_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return self._write(s)

    @router.delete("/plans/{plan_id}", response_model=StateOut)
    def cancel(self, plan_id: UUID, revision: int = Query(ge=0)):
        s = self._service(revision)
        before = s.state.plans.get(str(plan_id))
        try:
            s.cancel(plan_id)
            self._sync_shopping(None, before)
            return self._write(s)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.post("/plans/{plan_id}/consume/{entry_id}", response_model=StateOut)
    def consume(self, plan_id: UUID, entry_id: UUID, revision: int = Query(ge=0)):
        s = self._service(revision)
        try:
            s.consume(plan_id, entry_id, self.user.id)
            return self._write(s)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("/plans/{plan_id}/summary")
    def summary(self, plan_id: UUID):
        state = self._live(self._service().state)
        plan = state.plans.get(str(plan_id))
        if not plan:
            raise HTTPException(404, "Plan not found")
        return plan_summary(plan, state)

    @router.put("/plans/{plan_id}/shopping", response_model=StateOut)
    def check_items(self, plan_id: UUID, data: list[str], revision: int = Query(ge=0)):
        s = self._service(revision)
        plan = s.state.plans.get(str(plan_id))
        if not plan:
            raise HTTPException(404, "Plan not found")
        valid = {i["id"] for i in plan_summary(plan, s.state)["shopping"]}
        if len(data) > 1000 or not set(data) <= valid:
            raise HTTPException(422, "Unknown shopping item")
        plan.checked_items = list(dict.fromkeys(data))
        return self._write(s)

    @router.post("/plans/{plan_id}/shopping-list/{list_id}", response_model=StateOut)
    def add_to_shopping_list(self, plan_id: UUID, list_id: UUID, revision: int = Query(ge=0)):
        """Link the week to a native list and add its fresh cooking as recipes (with portions).

        Afterwards the list follows changes of the week automatically; calling again for the same list is a no-op.
        """
        s = self._service(revision)
        plan = s.state.plans.get(str(plan_id))
        if not plan:
            raise HTTPException(404, "Plan not found")
        if not self.repos.group_shopping_lists.get_one(list_id):
            raise HTTPException(404, "Shopping list not found")
        before = plan.model_copy(deep=True)
        if plan.shopping_list_id != list_id:
            before.shopping_servings = {}
        plan.shopping_list_id = before.shopping_list_id = list_id
        self._sync_shopping(plan, before)
        return self._write(s)

    @router.post("/batches", response_model=StateOut)
    def add_batch(self, data: BatchIn, revision: int = Query(ge=0)):
        s = self._service(revision)
        try:
            s.add_batch(data)
            return self._write(s)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("/stock")
    def stock(self):
        state = self._live(self._service().state)
        return [
            {
                **b.model_dump(mode="json"),
                "reserved": reserved(state, k),
                "available": b.remaining - reserved(state, k),
            }
            for k, b in state.batches.items()
        ]

    @router.post("/movements", response_model=StateOut)
    def movement(self, data: MovementIn, revision: int = Query(ge=0)):
        s = self._service(revision)
        try:
            s.move(data, self.user.id)
            return self._write(s)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    def _personal(self, revision: int | None = None) -> tuple[RepositoryHouseholdPlanner, int, PersonalState]:
        repo = self._repo(private=True)
        version, payload = repo.read()
        if revision is not None and version != revision:
            raise HTTPException(409, "Personal data changed. Reload before writing.")
        return repo, version, PersonalState.model_validate(payload)

    def _save_personal(self, repo: RepositoryHouseholdPlanner, revision: int, state: PersonalState) -> PersonalOut:
        try:
            revision = repo.save(revision, state.model_dump(mode="json"))
        except RevisionConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        return self._personal_out(revision, state)

    def _personal_out(self, revision: int, state: PersonalState) -> PersonalOut:
        now = datetime.now(UTC)
        last = state.active.confirmed_at if state.active else None
        due = not last or (now.year, now.month) > (last.year, last.month)
        return PersonalOut(revision=revision, state=state, review_due=due)

    @router.get("/me", response_model=PersonalOut)
    def personal(self):
        _, revision, state = self._personal()
        return self._personal_out(revision, state)

    @router.put("/me/profile", response_model=PersonalOut)
    def profile(self, data: ProfileIn, revision: int = Query(ge=0)):
        repo, version, state = self._personal(revision)
        state.profile = data
        return self._save_personal(repo, version, state)

    @router.post("/me/health", response_model=PersonalOut)
    def health(self, data: HealthSyncIn, revision: int = Query(ge=0)):
        repo, version, state = self._personal(revision)
        for key in data.deleted_ids:
            state.observations.pop(key, None)
        for o in data.observations:
            state.observations[o.id] = o
        if len(state.observations) > 20000:
            raise HTTPException(422, "History limit reached; remove old measurements before syncing")
        return self._save_personal(repo, version, state)

    @router.delete("/me/health", response_model=PersonalOut)
    def clear_health(self, revision: int = Query(ge=0)):
        repo, version, state = self._personal(revision)
        state.observations.clear()
        # Derived proposals also contain health inputs.
        state.revisions.clear()
        state.active = None
        return self._save_personal(repo, version, state)

    @router.post("/me/goals/propose", response_model=PersonalOut)
    def propose_goals(self, revision: int = Query(ge=0)):
        repo, version, state = self._personal(revision)
        try:
            state.revisions.append(monthly_proposal(state))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return self._save_personal(repo, version, state)

    @router.post("/me/goals/manual", response_model=PersonalOut)
    def manual_goals(self, data: GoalsIn, revision: int = Query(ge=0)):
        repo, version, state = self._personal(revision)
        state.revisions.append(
            GoalRevision(
                created_at=datetime.now(UTC), goals=data, explanation="Manually supplied targets; pending confirmation."
            )
        )
        return self._save_personal(repo, version, state)

    @router.post("/me/goals/{goal_id}/confirm", response_model=PersonalOut)
    def confirm_goals(self, goal_id: UUID, revision: int = Query(ge=0)):
        repo, version, state = self._personal(revision)
        proposal = next((r for r in state.revisions if r.id == goal_id), None)
        if not proposal:
            raise HTTPException(404, "Proposal not found")
        if not proposal.confirmed_at:
            proposal.confirmed_at = datetime.now(UTC)
        state.active = proposal.model_copy(deep=True)
        return self._save_personal(repo, version, state)
