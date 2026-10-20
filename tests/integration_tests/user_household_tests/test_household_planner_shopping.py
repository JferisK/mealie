"""Week plan -> native shopping list: dishes and portions are visible and the list follows plan changes."""

from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from mealie.schema.household.group_shopping_list import ShoppingListSave
from mealie.schema.recipe.recipe import Recipe
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient, SaveIngredientFood, SaveIngredientUnit
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser

BASE = "/api/households/planning"
# Tests share one household; each uses its own week so plan/list links do not leak between them.
WEEKS = iter(date(2026, 11, 2) + timedelta(weeks=n) for n in range(100))


def revision(api_client: TestClient, user: TestUser) -> int:
    return api_client.get(BASE, headers=user.token).json()["revision"]


def dish(api_client: TestClient, user: TestUser, food, unit, grams: float, servings: float | None = 4) -> str:
    """A structured recipe (quantity + unit + food) for `servings`, with planner facts."""
    recipe = user.repos.recipes.create(
        Recipe(
            user_id=user.user_id,
            group_id=user.group_id,
            name=random_string(10),
            recipe_servings=servings or 0,
            recipe_ingredient=[RecipeIngredient(quantity=grams, unit=unit, food=food)],
        )
    )
    facts = {
        "recipe_id": str(recipe.id),
        "servings": servings or 4,
        "ingredients": [{"name": food.name, "grams": grams, "state": "raw"}],
    }
    response = api_client.put(
        f"{BASE}/recipe-facts?revision={revision(api_client, user)}", json=facts, headers=user.token
    )
    assert response.status_code == 200, response.text
    if servings is None:
        # mirror_native_nutrition copies the facts servings; clear it again to model a recipe without a yield
        user.repos.recipes.patch(recipe.slug, {"recipe_servings": 0})
    return str(recipe.id)


def chicken(user: TestUser):
    food = user.repos.ingredient_foods.create(SaveIngredientFood(name=random_string(8), group_id=user.group_id))
    unit = user.repos.ingredient_units.create(
        SaveIngredientUnit(name=random_string(6), abbreviation="g", group_id=user.group_id)
    )
    return food, unit


def plan_week(api_client: TestClient, user: TestUser, monday: date, servings: dict[str, float]) -> dict:
    entries = [
        {
            "id": str(uuid4()),
            "user_id": str(user.user_id),
            "recipe_id": recipe_id,
            "day": str(monday + timedelta(days=n)),
            "meal": "lunch",
            "servings": amount,
        }
        for n, (recipe_id, amount) in enumerate(servings.items())
    ]
    response = api_client.put(
        f"{BASE}/weeks/{monday}?revision={revision(api_client, user)}",
        json={"id": str(uuid4()), "start": str(monday), "entries": entries},
        headers=user.token,
    )
    assert response.status_code == 200, response.text
    return next((p for p in response.json()["state"]["plans"].values() if p["start"] == str(monday)), {})


def new_list(user: TestUser):
    return user.repos.group_shopping_lists.create(
        ShoppingListSave(name=random_string(8), group_id=user.group_id, user_id=user.user_id)
    )


def add_week(api_client: TestClient, user: TestUser, plan_id: str, list_id) -> dict:
    response = api_client.post(
        f"{BASE}/plans/{plan_id}/shopping-list/{list_id}?revision={revision(api_client, user)}", headers=user.token
    )
    assert response.status_code == 200, response.text
    return response.json()


def contents(user: TestUser, list_id) -> tuple[list[float], dict[str, float]]:
    out = user.repos.group_shopping_lists.get_one(list_id)
    quantities = sorted(round(i.quantity, 2) for i in out.list_items if not i.checked)
    refs = {str(r.recipe_id): round(r.recipe_quantity, 3) for r in out.recipe_references}
    return quantities, refs


def test_week_shows_dishes_and_sums_same_food(api_client: TestClient, unique_user: TestUser):
    monday = next(WEEKS)
    food, unit = chicken(unique_user)
    curry = dish(api_client, unique_user, food, unit, 600)
    oven = dish(api_client, unique_user, food, unit, 400)
    plan = plan_week(api_client, unique_user, monday, {curry: 4, oven: 4})
    shopping = new_list(unique_user)

    state = add_week(api_client, unique_user, plan["id"], shopping.id)

    assert contents(unique_user, shopping.id) == ([1000], {curry: 1, oven: 1})
    linked = state["state"]["plans"][plan["id"]]
    assert linked["shopping_list_id"] == str(shopping.id)
    assert linked["shopping_servings"] == {curry: 4, oven: 4}


def test_list_follows_week_changes(api_client: TestClient, unique_user: TestUser):
    monday = next(WEEKS)
    food, unit = chicken(unique_user)
    curry = dish(api_client, unique_user, food, unit, 600)
    oven = dish(api_client, unique_user, food, unit, 400)
    plan = plan_week(api_client, unique_user, monday, {curry: 4, oven: 4})
    shopping = new_list(unique_user)
    add_week(api_client, unique_user, plan["id"], shopping.id)

    plan_week(api_client, unique_user, monday, {curry: 2, oven: 4})  # fewer curry portions
    assert contents(unique_user, shopping.id) == ([700], {curry: 0.5, oven: 1})

    plan_week(api_client, unique_user, monday, {curry: 6, oven: 4})  # more curry portions
    assert contents(unique_user, shopping.id) == ([1300], {curry: 1.5, oven: 1})

    plan = plan_week(api_client, unique_user, monday, {oven: 4})  # curry removed from the week
    assert contents(unique_user, shopping.id) == ([400], {oven: 1})

    response = api_client.delete(
        f"{BASE}/plans/{plan['id']}?revision={revision(api_client, unique_user)}", headers=unique_user.token
    )
    assert response.status_code == 200, response.text
    assert contents(unique_user, shopping.id) == ([], {})


def test_frozen_portions_need_no_purchase(api_client: TestClient, unique_user: TestUser):
    monday = next(WEEKS)
    food, unit = chicken(unique_user)
    curry = dish(api_client, unique_user, food, unit, 600)
    batch = {"id": str(uuid4()), "recipe_id": curry, "servings": 2, "frozen_on": "2026-10-30", "location": "Keller"}
    response = api_client.post(
        f"{BASE}/batches?revision={revision(api_client, unique_user)}", json=batch, headers=unique_user.token
    )
    assert response.status_code == 200, response.text
    entry = {
        "id": str(uuid4()),
        "user_id": str(unique_user.user_id),
        "recipe_id": curry,
        "day": str(monday),
        "meal": "dinner",
        "servings": 2,
        "batch_id": batch["id"],
    }
    response = api_client.put(
        f"{BASE}/weeks/{monday}?revision={revision(api_client, unique_user)}",
        json={"id": str(uuid4()), "start": str(monday), "entries": [entry]},
        headers=unique_user.token,
    )
    assert response.status_code == 200, response.text
    plan_id = next(p["id"] for p in response.json()["state"]["plans"].values() if p["start"] == str(monday))
    shopping = new_list(unique_user)

    add_week(api_client, unique_user, plan_id, shopping.id)

    assert contents(unique_user, shopping.id) == ([], {})


def test_recipe_without_servings_is_rejected(api_client: TestClient, unique_user: TestUser):
    monday = next(WEEKS)
    food, unit = chicken(unique_user)
    recipe = dish(api_client, unique_user, food, unit, 600, servings=None)
    plan = plan_week(api_client, unique_user, monday, {recipe: 1})
    shopping = new_list(unique_user)
    response = api_client.post(
        f"{BASE}/plans/{plan['id']}/shopping-list/{shopping.id}?revision={revision(api_client, unique_user)}",
        headers=unique_user.token,
    )
    assert response.status_code == 422
    assert contents(unique_user, shopping.id) == ([], {})


def test_unknown_plan_or_foreign_list(api_client: TestClient, unique_user: TestUser, h2_user: TestUser):
    monday = next(WEEKS)
    food, unit = chicken(unique_user)
    plan = plan_week(api_client, unique_user, monday, {dish(api_client, unique_user, food, unit, 100): 1})
    own, foreign = new_list(unique_user), new_list(h2_user)
    rev = revision(api_client, unique_user)

    unknown = api_client.post(
        f"{BASE}/plans/{uuid4()}/shopping-list/{own.id}?revision={rev}", headers=unique_user.token
    )
    assert unknown.status_code == 404
    response = api_client.post(
        f"{BASE}/plans/{plan['id']}/shopping-list/{foreign.id}?revision={rev}", headers=unique_user.token
    )
    assert response.status_code == 404
    assert contents(h2_user, foreign.id) == ([], {})
