"""Versioned contracts for the optional household planning extension."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Nutrients(Contract):
    calories: Nonnegative | None = None
    protein: Nonnegative | None = None
    carbohydrate: Nonnegative | None = None
    fat: Nonnegative | None = None
    fiber: Nonnegative | None = None


class IngredientIn(Contract):
    name: str = Field(min_length=1, max_length=200)
    grams: Positive
    state: Literal["raw", "cooked", "as_sold"] = "as_sold"
    per_100g: Nutrients = Field(default_factory=Nutrients)
    source: str = Field(default="", max_length=1000)


class RecipeFactsIn(Contract):
    recipe_id: UUID
    servings: Positive
    cooked_weight_g: Positive | None = None
    ingredients: list[IngredientIn] = Field(default_factory=list, max_length=200)
    gluten_free: Literal["yes", "no", "unknown"] = "unknown"
    lactose_free: Literal["yes", "no", "unknown"] = "unknown"
    freezer_friendly: Literal["yes", "no", "unknown"] = "unknown"
    evidence: str = Field(default="", max_length=2000)
    storage_instructions: str = Field(default="", max_length=4000)
    reheating_instructions: str = Field(default="", max_length=4000)


class RecipeFactsOut(RecipeFactsIn):
    name: str
    slug: str
    image: str | None = None
    per_serving: Nutrients
    coverage: float
    updated_at: datetime


class AllocationIn(Contract):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    recipe_id: UUID
    day: date
    meal: Literal["breakfast", "lunch", "dinner", "snack"]
    servings: Positive
    batch_id: UUID | None = None
    note: str = Field(default="", max_length=500)


class PlanIn(Contract):
    id: UUID = Field(default_factory=uuid4)
    start: date
    entries: list[AllocationIn] = Field(default_factory=list, max_length=150)

    @model_validator(mode="after")
    def valid_week(self):
        if self.start.weekday() != 0:
            raise ValueError("Week starts on Monday")
        if any(not 0 <= (e.day - self.start).days < 7 for e in self.entries):
            raise ValueError("All entries must belong to this week")
        if len({e.id for e in self.entries}) != len(self.entries):
            raise ValueError("Allocation IDs must be unique")
        return self


class PlanOut(PlanIn):
    confirmed_at: datetime
    native_ids: list[int] = Field(default_factory=list)
    consumed: list[UUID] = Field(default_factory=list)
    checked_items: list[str] = Field(default_factory=list)
    recipe_snapshots: dict[str, RecipeFactsOut] = Field(default_factory=dict)
    shopping_list_id: UUID | None = None
    """Native shopping list that follows this week's fresh cooking."""
    shopping_servings: dict[str, float] = Field(default_factory=dict)
    """Servings per recipe already transferred to the linked list."""


class BatchIn(Contract):
    id: UUID = Field(default_factory=uuid4)
    recipe_id: UUID
    servings: Positive
    frozen_on: date
    location: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=1000)


class BatchOut(BatchIn):
    remaining: Nonnegative
    facts: RecipeFactsOut


class MovementIn(Contract):
    id: UUID = Field(default_factory=uuid4)
    batch_id: UUID
    kind: Literal["withdraw", "discard", "correction"]
    servings: Nonnegative
    note: str = Field(default="", max_length=500)


class MovementOut(MovementIn):
    at: datetime
    actor: UUID


class IdeaIn(Contract):
    id: UUID = Field(default_factory=uuid4)
    week_start: date
    recipe_id: UUID
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def monday(self):
        if self.week_start.weekday() != 0:
            raise ValueError("Week starts on Monday")
        return self


class IdeaOut(IdeaIn):
    name: str
    slug: str
    image: str | None = None
    proposed_by: UUID
    created_at: datetime
    likes: list[UUID] = Field(default_factory=list)


class PlannerState(Contract):
    facts: dict[str, RecipeFactsOut] = Field(default_factory=dict)
    batches: dict[str, BatchOut] = Field(default_factory=dict)
    movements: dict[str, MovementOut] = Field(default_factory=dict)
    plans: dict[str, PlanOut] = Field(default_factory=dict)
    ideas: dict[str, IdeaOut] = Field(default_factory=dict)


class StateOut(Contract):
    revision: int
    state: PlannerState


class GoalsIn(Contract):
    calories: Positive
    protein: Positive
    carbohydrate: Nonnegative | None = None
    fat: Nonnegative | None = None


class ProfileIn(Contract):
    birth_date: date | None = None
    height_cm: Annotated[float, Field(ge=100, le=250)] | None = None
    equation_sex: Literal["male", "female"] | None = None
    activity_factor: Annotated[float, Field(ge=1.2, le=2.4)] = 1.4
    deficit_kcal: Annotated[float, Field(ge=0, le=750)] = 400
    protein_reference_kg: Positive | None = None
    protein_g_per_kg: Annotated[float, Field(ge=0.8, le=2.2)] = 1.2
    gluten_free: bool = False
    lactose_free: bool = False
    avoid_traces: bool = False
    dislikes: list[str] = Field(default_factory=list, max_length=100)


class ObservationIn(Contract):
    id: str = Field(min_length=1, max_length=200)
    kind: Literal[
        "weight_kg", "height_cm", "body_fat_percent", "steps", "active_kcal", "resting_kcal", "workout_minutes"
    ]
    value: Nonnegative
    at: datetime
    source: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def valid_measurement(self):
        if self.at.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        limits = {"weight_kg": (20, 500), "height_cm": (100, 250), "body_fat_percent": (1, 80)}
        if self.kind in limits and not limits[self.kind][0] <= self.value <= limits[self.kind][1]:
            raise ValueError("Measurement outside supported range")
        return self


class HealthSyncIn(Contract):
    observations: list[ObservationIn] = Field(default_factory=list, max_length=1000)
    deleted_ids: list[str] = Field(default_factory=list, max_length=1000)


class GoalRevision(Contract):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime
    goals: GoalsIn
    explanation: str
    inputs: dict[str, float | str] = Field(default_factory=dict)
    confirmed_at: datetime | None = None


class PersonalState(Contract):
    profile: ProfileIn = Field(default_factory=ProfileIn)
    observations: dict[str, ObservationIn] = Field(default_factory=dict)
    revisions: list[GoalRevision] = Field(default_factory=list)
    active: GoalRevision | None = None


class PersonalOut(Contract):
    revision: int
    state: PersonalState
    review_due: bool
