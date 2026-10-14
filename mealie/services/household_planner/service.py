from datetime import UTC, datetime
from uuid import UUID

from mealie.db.models.household.mealplan import GroupMealPlan
from mealie.db.models.recipe.nutrition import Nutrition
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.repos.repository_household_planner import RepositoryHouseholdPlanner, RevisionConflict
from mealie.schema.household_planner.models import (
    BatchIn,
    BatchOut,
    MovementIn,
    MovementOut,
    PlanIn,
    PlannerState,
    PlanOut,
    RecipeFactsIn,
    RecipeFactsOut,
)
from mealie.services.household_planner.calculations import nutrition, plan_summary, reserved


class PlannerService:
    def __init__(self, repository: RepositoryHouseholdPlanner):
        self.repository = repository
        self.revision, payload = repository.read()
        self.state = PlannerState.model_validate(payload)

    def expect(self, revision: int) -> None:
        if revision != self.revision:
            raise RevisionConflict("Planner changed. Reload before writing.")

    def save(self) -> int:
        self.revision = self.repository.save(self.revision, self.state.model_dump(mode="json"))
        return self.revision

    def facts(self, data: RecipeFactsIn, name: str, slug: str, image: str | None) -> None:
        per_serving, coverage = nutrition(data)
        self.state.facts[str(data.recipe_id)] = RecipeFactsOut(
            **data.model_dump(),
            name=name,
            slug=slug,
            image=image,
            per_serving=per_serving,
            coverage=coverage,
            updated_at=datetime.now(UTC),
        )

    def mirror_native_nutrition(self, recipe_id: UUID) -> None:
        recipe = self.repository.session.get(RecipeModel, recipe_id)
        if not recipe:
            raise ValueError("Recipe no longer exists")
        facts = self.state.facts[str(recipe_id)]
        values = facts.per_serving

        def text(value: float | None) -> str | None:
            return str(value) if value is not None else None

        recipe.recipe_servings = facts.servings
        recipe.nutrition = Nutrition(
            calories=text(values.calories),
            protein_content=text(values.protein),
            carbohydrate_content=text(values.carbohydrate),
            fat_content=text(values.fat),
            fiber_content=text(values.fiber),
        )
        # The planner document and native nutrition commit together in save().

    def add_batch(self, data: BatchIn) -> None:
        key = str(data.id)
        if key in self.state.batches:
            existing = self.state.batches[key]
            if BatchIn.model_validate({k: getattr(existing, k) for k in BatchIn.model_fields}) != data:
                raise ValueError("Batch ID already used for different data")
            return
        facts = self.state.facts.get(str(data.recipe_id))
        if not facts:
            raise ValueError("Add recipe facts before freezing portions")
        self.state.batches[key] = BatchOut(
            **data.model_dump(), remaining=data.servings, facts=facts.model_copy(deep=True)
        )

    def move(self, data: MovementIn, actor: UUID) -> None:
        key = str(data.id)
        if key in self.state.movements:
            previous = self.state.movements[key]
            if any(getattr(previous, k) != getattr(data, k) for k in MovementIn.model_fields):
                raise ValueError("Movement ID already used for different data")
            return
        batch = self.state.batches.get(str(data.batch_id))
        if not batch:
            raise ValueError("Unknown batch")
        remaining = data.servings if data.kind == "correction" else batch.remaining - data.servings
        if remaining < reserved(self.state, str(data.batch_id)) - 1e-8:
            raise ValueError(
                "Insufficient unreserved stock. Consume the planned entry or cancel its reservation first."
            )
        batch.remaining = max(0, remaining)
        self.state.movements[key] = MovementOut(**data.model_dump(), at=datetime.now(UTC), actor=actor)

    def validate_plan(self, plan: PlanIn, member_ids: set[UUID]) -> dict:
        wanted: dict[str, float] = {}
        for e in plan.entries:
            if e.user_id not in member_ids:
                raise ValueError("Allocation user is not a household member")
            if e.batch_id:
                batch = self.state.batches.get(str(e.batch_id))
                if not batch or batch.recipe_id != e.recipe_id:
                    raise ValueError("Batch does not match recipe")
                wanted[str(e.batch_id)] = wanted.get(str(e.batch_id), 0) + e.servings
            elif str(e.recipe_id) not in self.state.facts:
                raise ValueError("Add structured recipe facts before planning")
        for key, quantity in wanted.items():
            if quantity + reserved(self.state, key, str(plan.id)) > self.state.batches[key].remaining + 1e-8:
                raise ValueError("Plan requests more frozen portions than available")
        return plan_summary(plan, self.state)

    def confirm(self, plan: PlanIn, member_ids: set[UUID], group_id: UUID, actor: UUID) -> None:
        existing = self.state.plans.get(str(plan.id))
        if existing:
            if PlanIn.model_validate({k: getattr(existing, k) for k in PlanIn.model_fields}) == plan:
                return
            raise ValueError("Confirmed plans are immutable. Cancel and create a new plan.")
        if any(p.start == plan.start for p in self.state.plans.values()):
            raise ValueError("A plan already exists for this week. Cancel it before replacing it.")
        self.validate_plan(plan, member_ids)
        # Mirror each unique shared dish into the native Mealie planner, in the same transaction.
        native = []
        seen = set()
        for e in plan.entries:
            key = (e.day, e.meal, e.recipe_id)
            if key in seen:
                continue
            seen.add(key)
            facts = self.state.batches[str(e.batch_id)].facts if e.batch_id else self.state.facts[str(e.recipe_id)]
            row = GroupMealPlan(
                session=self.repository.session,
                date=e.day,
                entry_type=e.meal,
                title=facts.name,
                text=f"Household planner:{plan.id}",
                recipe_id=e.recipe_id,
                group_id=group_id,
                user_id=actor,
            )
            self.repository.session.add(row)
            self.repository.session.flush()
            native.append(row.id)
        self.state.plans[str(plan.id)] = PlanOut(
            **plan.model_dump(),
            confirmed_at=datetime.now(UTC),
            native_ids=native,
            recipe_snapshots={
                str(e.recipe_id): self.state.facts[str(e.recipe_id)].model_copy(deep=True)
                for e in plan.entries
                if not e.batch_id
            },
        )

    def cancel(self, plan_id: UUID) -> None:
        plan = self.state.plans.pop(str(plan_id), None)
        if not plan:
            raise ValueError("Unknown plan")
        for native_id in plan.native_ids:
            row = self.repository.session.get(GroupMealPlan, native_id)
            if row and row.text == f"Household planner:{plan.id}":
                self.repository.session.delete(row)

    def consume(self, plan_id: UUID, entry_id: UUID, actor: UUID) -> None:
        plan = self.state.plans.get(str(plan_id))
        if not plan:
            raise ValueError("Unknown plan")
        entry = next((e for e in plan.entries if e.id == entry_id), None)
        if not entry:
            raise ValueError("Unknown allocation")
        if entry_id in plan.consumed:
            return
        plan.consumed.append(entry_id)
        if entry.batch_id:
            self.move(
                MovementIn(
                    id=entry.id,
                    batch_id=entry.batch_id,
                    kind="withdraw",
                    servings=entry.servings,
                    note="Confirmed meal consumption",
                ),
                actor,
            )
