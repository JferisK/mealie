from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from mealie.db.models.users.users import User
from mealie.repos.repository_household_planner import RepositoryHouseholdPlanner, RevisionConflict
from mealie.routes._base import controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.schema.household_planner.models import (
    BatchIn,
    GoalRevision,
    GoalsIn,
    HealthSyncIn,
    MovementIn,
    PersonalOut,
    PersonalState,
    PlanIn,
    ProfileIn,
    RecipeFactsIn,
    StateOut,
)
from mealie.services.household_planner.calculations import monthly_proposal, plan_summary, reserved
from mealie.services.household_planner.service import PlannerService

router = APIRouter(prefix="/households/planning", tags=["Households: Planning"])


@controller(router)
class HouseholdPlannerController(BaseUserController):
    def _repo(self, private: bool = False) -> RepositoryHouseholdPlanner:
        key = f"user:{self.user.id}" if private else f"household:{self.household_id}"
        return RepositoryHouseholdPlanner(self.session, key)

    def _service(self, revision: int | None = None) -> PlannerService:
        service = PlannerService(self._repo())
        if revision is not None:
            try:
                service.expect(revision)
            except RevisionConflict as exc:
                raise HTTPException(409, str(exc)) from exc
        return service

    def _members(self) -> set[UUID]:
        return {u.id for u in self.session.query(User).filter(User.household_id == self.household_id).all()}

    def _write(self, service: PlannerService) -> StateOut:
        try:
            service.save()
        except RevisionConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        return StateOut(revision=service.revision, state=service.state)

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
        return StateOut(revision=s.revision, state=s.state)

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
        recipe = self.repos.recipes.get_one(data.recipe_id)
        if not recipe or recipe.household_id != self.household_id:
            raise HTTPException(404, "Recipe not found in this household")
        if (data.gluten_free == "yes" or data.lactose_free == "yes") and not data.evidence.strip():
            raise HTTPException(422, "Verified dietary suitability requires evidence")
        s.facts(data, recipe.name, recipe.slug, recipe.image)
        s.mirror_native_nutrition(data.recipe_id)
        return self._write(s)

    @router.post("/preview")
    def preview(self, data: PlanIn):
        s = self._service()
        return {"revision": s.revision, "plan": data, "summary": self._check_plan(s, data)}

    @router.post("/confirm", response_model=StateOut)
    def confirm(self, data: PlanIn, revision: int = Query(ge=0)):
        s = self._service(revision)
        if str(data.id) not in s.state.plans:
            self._check_plan(s, data)
        try:
            s.confirm(data, self._members(), self.group_id, self.user.id)
            return self._write(s)
        except ValueError as exc:
            self.session.rollback()
            raise HTTPException(422, str(exc)) from exc

    @router.delete("/plans/{plan_id}", response_model=StateOut)
    def cancel(self, plan_id: UUID, revision: int = Query(ge=0)):
        s = self._service(revision)
        try:
            s.cancel(plan_id)
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
        s = self._service()
        plan = s.state.plans.get(str(plan_id))
        if not plan:
            raise HTTPException(404, "Plan not found")
        return plan_summary(plan, s.state)

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
        s = self._service()
        return [
            {
                **b.model_dump(mode="json"),
                "reserved": reserved(s.state, k),
                "available": b.remaining - reserved(s.state, k),
            }
            for k, b in s.state.batches.items()
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
