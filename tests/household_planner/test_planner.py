"""Focused regression suite; runnable independently of LDAP and the full app fixture."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import mealie.db.models._all_models  # noqa: F401
from mealie.db.models._model_base import SqlAlchemyBase
from mealie.db.models.household.mealplan import GroupMealPlan
from mealie.repos.repository_household_planner import RepositoryHouseholdPlanner, RevisionConflict
from mealie.schema.household_planner.models import (
    AllocationIn,
    BatchIn,
    IngredientIn,
    MovementIn,
    Nutrients,
    ObservationIn,
    PersonalState,
    PlanIn,
    ProfileIn,
    RecipeFactsIn,
)
from mealie.services.household_planner.calculations import monthly_proposal, nutrition, reserved
from mealie.services.household_planner.service import PlannerService

MONDAY = date(2026, 10, 12)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SqlAlchemyBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def service(session):
    return PlannerService(RepositoryHouseholdPlanner(session, "household:test"))


def facts():
    return RecipeFactsIn(
        recipe_id=uuid4(),
        servings=2,
        gluten_free="yes",
        lactose_free="yes",
        ingredients=[
            IngredientIn(
                name="Rice", grams=200, state="raw", source="test label", per_100g=Nutrients(calories=350, protein=7)
            )
        ],
    )


def prepared(service):
    f = facts()
    service.facts(f, "Rice", "rice", None)
    batch = BatchIn(recipe_id=f.recipe_id, servings=4, frozen_on=MONDAY, location="Drawer 1")
    service.add_batch(batch)
    return f, batch


def test_nutrition_per_recipe_servings_and_unknown():
    f = facts()
    result, coverage = nutrition(f)
    assert result.calories == 350 and result.protein == 7 and result.fat is None
    assert coverage == 1
    f.ingredients.append(IngredientIn(name="Sauce", grams=100))
    result, coverage = nutrition(f)
    assert result.calories is None and result.protein is None
    assert coverage == 0.667


def test_unsourced_values_are_not_treated_as_known():
    f = facts()
    f.ingredients[0].source = "  "
    assert nutrition(f)[0].calories is None


def test_reserve_consume_retry_cancel_and_native_mirror(service, session):
    f, batch = prepared(service)
    user, group = uuid4(), uuid4()
    entry = AllocationIn(user_id=user, recipe_id=f.recipe_id, day=MONDAY, meal="lunch", servings=1.5, batch_id=batch.id)
    plan = PlanIn(start=MONDAY, entries=[entry])
    preview = service.validate_plan(plan, {user})
    assert preview["shopping"] == [] and preview["cooking"] == []
    assert service.state.batches[str(batch.id)].remaining == 4
    service.confirm(plan, {user}, group, user)
    service.save()
    assert reserved(service.state, str(batch.id)) == 1.5
    assert len(session.scalars(select(GroupMealPlan)).all()) == 1
    service.confirm(plan, {user}, group, user)
    assert len(session.scalars(select(GroupMealPlan)).all()) == 1
    service.consume(plan.id, entry.id, user)
    service.consume(plan.id, entry.id, user)
    assert service.state.batches[str(batch.id)].remaining == 2.5
    assert reserved(service.state, str(batch.id)) == 0
    service.cancel(plan.id)
    service.save()
    assert service.state.batches[str(batch.id)].remaining == 2.5
    assert session.scalars(select(GroupMealPlan)).all() == []


def test_cannot_overbook_or_withdraw_reserved_stock(service):
    f, batch = prepared(service)
    user = uuid4()
    plan = PlanIn(
        start=MONDAY,
        entries=[
            AllocationIn(user_id=user, recipe_id=f.recipe_id, day=MONDAY, meal="dinner", servings=3, batch_id=batch.id)
        ],
    )
    service.confirm(plan, {user}, uuid4(), user)
    with pytest.raises(ValueError, match="Insufficient"):
        service.move(MovementIn(batch_id=batch.id, kind="withdraw", servings=2), user)
    other = plan.model_copy(deep=True)
    other.id = uuid4()
    with pytest.raises(ValueError, match="more frozen"):
        service.validate_plan(other, {user})
    with pytest.raises(ValueError, match="household member"):
        service.validate_plan(plan, {uuid4()})


def test_frozen_facts_are_snapshot_and_movements_idempotent(service):
    f, batch = prepared(service)
    f.ingredients[0].per_100g.calories = 999
    service.facts(f, "Edited", "rice", None)
    assert service.state.batches[str(batch.id)].facts.per_serving.calories == 350
    move = MovementIn(batch_id=batch.id, kind="withdraw", servings=1)
    service.move(move, uuid4())
    service.move(move, uuid4())
    assert service.state.batches[str(batch.id)].remaining == 3
    with pytest.raises(ValueError, match="already used"):
        service.move(move.model_copy(update={"servings": 2}), uuid4())


def test_combined_shopping_scales_personal_portions(service):
    f = facts()
    service.facts(f, "Rice", "rice", None)
    users = {uuid4(), uuid4()}
    entries = [
        AllocationIn(user_id=u, recipe_id=f.recipe_id, day=MONDAY, meal="lunch", servings=n)
        for n, u in enumerate(users, start=1)
    ]
    summary = service.validate_plan(PlanIn(start=MONDAY, entries=entries), users)
    assert summary["shopping"][0]["grams"] == 300
    assert summary["cooking"][0]["servings"] == 3
    assert sorted(d["nutrients"]["calories"] for d in summary["days"]) == [350, 700]
    assert all(d["nutrients"]["fat"] is None for d in summary["days"])


def test_revision_conflict_and_scope_isolation(session):
    a = RepositoryHouseholdPlanner(session, "user:a")
    b = RepositoryHouseholdPlanner(session, "user:b")
    assert a.save(0, {"private": 1}) == 1
    assert b.read() == (0, {})
    with pytest.raises(RevisionConflict):
        a.save(0, {"lost": 1})
    assert a.save(1, {"private": 2}) == 2
    with pytest.raises(RevisionConflict):
        a.save(1, {"lost": 2})
    assert a.read() == (2, {"private": 2})


def test_monthly_formula_daily_weighting_and_no_automatic_activation():
    today = date(2026, 10, 14)
    state = PersonalState(
        profile=ProfileIn(
            birth_date=date(1996, 1, 1),
            height_cm=180,
            equation_sex="male",
            activity_factor=1.4,
            deficit_kcal=400,
            protein_reference_kg=80,
            protein_g_per_kg=1.2,
        )
    )
    for i in range(3):
        o = ObservationIn(
            id=str(i),
            kind="weight_kg",
            value=80,
            at=datetime(2026, 10, 14, tzinfo=UTC) - timedelta(days=i),
            source="fixture",
        )
        state.observations[o.id] = o
    result = monthly_proposal(state, today)
    assert result.goals.calories == 2092 and result.goals.protein == 96
    assert result.inputs["resting_kcal"] == 1780
    assert result.confirmed_at is None and state.active is None
    state.observations.pop("2")
    with pytest.raises(ValueError, match="three distinct"):
        monthly_proposal(state, today)


@pytest.mark.parametrize("field,value", [("servings", 0), ("servings", float("nan")), ("servings", -1)])
def test_reject_invalid_quantities(field, value):
    with pytest.raises(ValidationError):
        RecipeFactsIn(recipe_id=uuid4(), **{field: value})


def test_reject_wrong_week_and_naive_health_timestamp():
    with pytest.raises(ValidationError):
        PlanIn(start=MONDAY + timedelta(days=1))
    with pytest.raises(ValidationError):
        ObservationIn(
            id="bad",
            kind="weight_kg",
            value=80,
            at=datetime(2026, 10, 14, tzinfo=UTC).replace(tzinfo=None),
            source="fixture",
        )


def test_native_recipe_nutrition_uses_explicit_servings(service, session):
    from mealie.db.models.recipe.recipe import RecipeModel

    recipe = RecipeModel(
        session=session,
        name="Fixture rice",
        slug="fixture-rice",
        group_id=uuid4(),
        household_id=uuid4(),
        user_id=uuid4(),
    )
    session.add(recipe)
    session.flush()
    f = facts().model_copy(update={"recipe_id": recipe.id})
    service.facts(f, recipe.name, recipe.slug, None)
    service.mirror_native_nutrition(recipe.id)
    service.save()
    assert recipe.recipe_servings == 2
    assert recipe.nutrition.calories == "350.0"
    assert recipe.nutrition.fat_content is None
