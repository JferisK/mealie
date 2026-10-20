"""Week plan -> native shopping list: planner grams are summed across dishes, not copied as unscaled text."""

from uuid import uuid4

from fastapi.testclient import TestClient

from mealie.schema.household.group_shopping_list import ShoppingListItemCreate, ShoppingListSave
from mealie.schema.recipe.recipe import Recipe
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient, SaveIngredientUnit
from mealie.schema.response.pagination import PaginationQuery
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser

BASE = "/api/households/planning"
MONDAY = "2026-10-19"


def revision(api_client: TestClient, user: TestUser) -> int:
    return api_client.get(BASE, headers=user.token).json()["revision"]


def dish(api_client: TestClient, user: TestUser, chicken_grams: int, lines: list[str]) -> str:
    """Native ingredients are unparsed text, as in the household's real recipes."""
    recipe = user.repos.recipes.create(
        Recipe(
            user_id=user.user_id,
            group_id=user.group_id,
            name=random_string(10),
            recipe_ingredient=[RecipeIngredient(quantity=0, note=line) for line in lines],
        )
    )
    facts = {
        "recipe_id": str(recipe.id),
        "servings": 4,
        "ingredients": [{"name": "Hähnchenbrust", "grams": chicken_grams, "state": "raw"}],
    }
    response = api_client.put(
        f"{BASE}/recipe-facts?revision={revision(api_client, user)}", json=facts, headers=user.token
    )
    assert response.status_code == 200, response.text
    return str(recipe.id)


def plan_week(api_client: TestClient, user: TestUser, servings: dict[str, float]) -> str:
    entries = [
        {
            "id": str(uuid4()),
            "user_id": str(user.user_id),
            "recipe_id": recipe_id,
            "day": f"2026-10-{19 + n}",
            "meal": "lunch",
            "servings": amount,
        }
        for n, (recipe_id, amount) in enumerate(servings.items())
    ]
    response = api_client.put(
        f"{BASE}/weeks/{MONDAY}?revision={revision(api_client, user)}",
        json={"id": str(uuid4()), "start": MONDAY, "entries": entries},
        headers=user.token,
    )
    assert response.status_code == 200, response.text
    return next(p["id"] for p in response.json()["state"]["plans"].values() if p["start"] == MONDAY)


def new_list(user: TestUser):
    return user.repos.group_shopping_lists.create(
        ShoppingListSave(name=random_string(8), group_id=user.group_id, user_id=user.user_id)
    )


def items(user: TestUser, list_id) -> dict[str, tuple[float, str | None]]:
    out = user.repos.group_shopping_lists.get_one(list_id)
    return {i.note: (i.quantity, i.unit.abbreviation if i.unit else None) for i in out.list_items}


def unit_ids(user: TestUser) -> set:
    return {u.id for u in user.repos.ingredient_units.page_all(PaginationQuery(per_page=-1)).items}


def test_week_shopping_sums_and_scales_planner_grams(api_client: TestClient, unique_user: TestUser):
    curry = dish(api_client, unique_user, 600, ["600 g Hähnchenbrust", "2 EL Currypulver", "Salz, Pfeffer"])
    oven = dish(api_client, unique_user, 400, ["400 g Hähnchenbrust", "Salz, Pfeffer"])
    # 3 of 4 curry servings, 8 of 4 oven servings (doubled)
    plan_id = plan_week(api_client, unique_user, {curry: 3, oven: 8})
    shopping = new_list(unique_user)

    response = api_client.post(f"{BASE}/plans/{plan_id}/shopping-list/{shopping.id}", headers=unique_user.token)
    assert response.status_code == 200, response.text

    assert items(unique_user, shopping.id) == {
        "Hähnchenbrust": (600 * 3 / 4 + 400 * 8 / 4, "g"),
        "2 EL Currypulver": (0, None),
        "Salz, Pfeffer": (0, None),
    }


def test_week_shopping_merges_into_existing_gram_item(api_client: TestClient, unique_user: TestUser):
    first = dish(api_client, unique_user, 400, [])
    second = dish(api_client, unique_user, 600, [])
    plan_id = plan_week(api_client, unique_user, {first: 4, second: 4})
    gram = unique_user.repos.ingredient_units.create(
        SaveIngredientUnit(name=random_string(6), abbreviation="g", group_id=unique_user.group_id)
    )
    assert gram.standard_unit == "gram"
    shopping = new_list(unique_user)
    unique_user.repos.group_shopping_list_item.create(
        ShoppingListItemCreate(shopping_list_id=shopping.id, note="Hähnchenbrust", quantity=200, unit_id=gram.id)
    )

    units_before = unit_ids(unique_user)

    response = api_client.post(f"{BASE}/plans/{plan_id}/shopping-list/{shopping.id}", headers=unique_user.token)
    assert response.status_code == 200, response.text

    assert items(unique_user, shopping.id) == {"Hähnchenbrust": (1200, "g")}
    # An existing standardized gram unit is reused, no new unit per call.
    assert unit_ids(unique_user) == units_before


def test_week_shopping_unknown_plan_or_foreign_list(api_client: TestClient, unique_user: TestUser, h2_user: TestUser):
    recipe = dish(api_client, unique_user, 100, [])
    plan_id = plan_week(api_client, unique_user, {recipe: 1})
    own = new_list(unique_user)
    foreign = new_list(h2_user)

    assert (
        api_client.post(f"{BASE}/plans/{uuid4()}/shopping-list/{own.id}", headers=unique_user.token).status_code == 404
    )
    response = api_client.post(f"{BASE}/plans/{plan_id}/shopping-list/{foreign.id}", headers=unique_user.token)
    assert response.status_code == 404
    assert items(h2_user, foreign.id) == {}
