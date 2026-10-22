"""A deleted recipe disappears from the planner everywhere: facts, ideas, week plans, snapshots and the week list."""

from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.integration_tests.user_household_tests.test_household_planner_shopping import (
    add_week,
    chicken,
    contents,
    dish,
    new_list,
    revision,
)
from tests.utils import api_routes
from tests.utils.fixture_schemas import TestUser

BASE = "/api/households/planning"
WEEKS = iter(date(2028, 1, 3) + timedelta(weeks=n) for n in range(100))


def entry(user: TestUser, recipe_id: str, day: date, meal: str = "lunch") -> dict:
    return {
        "id": str(uuid4()),
        "user_id": str(user.user_id),
        "recipe_id": recipe_id,
        "day": str(day),
        "meal": meal,
        "servings": 4,
    }


def save(api_client: TestClient, user: TestUser, monday: date, entries: list[dict]):
    return api_client.put(
        f"{BASE}/weeks/{monday}?revision={revision(api_client, user)}",
        json={"start": str(monday), "entries": entries},
        headers=user.token,
    )


def delete_recipe(api_client: TestClient, user: TestUser, recipe_id: str) -> None:
    slug = user.repos.recipes.get_one(recipe_id, key="id").slug
    response = api_client.delete(api_routes.recipes_slug(slug), headers=user.token)
    assert response.status_code == 200, response.text


def test_deleted_recipe_leaves_the_planner(api_client: TestClient, unique_user: TestUser):
    monday = next(WEEKS)
    food, unit = chicken(unique_user)
    curry = dish(api_client, unique_user, food, unit, 600)
    chili = dish(api_client, unique_user, food, unit, 400)
    entries = [
        entry(unique_user, curry, monday, "breakfast"),
        entry(unique_user, curry, monday, "lunch"),
        entry(unique_user, chili, monday, "dinner"),
    ]
    response = save(api_client, unique_user, monday, entries)
    assert response.status_code == 200, response.text
    plan = next(p for p in response.json()["state"]["plans"].values() if p["start"] == str(monday))
    shopping = new_list(unique_user)
    add_week(api_client, unique_user, plan["id"], shopping.id)
    idea = {"id": str(uuid4()), "week_start": str(monday), "recipe_id": curry}
    rev = revision(api_client, unique_user)
    assert api_client.post(f"{BASE}/ideas?revision={rev}", json=idea, headers=unique_user.token).status_code == 200

    delete_recipe(api_client, unique_user, curry)

    state = api_client.get(BASE, headers=unique_user.token).json()["state"]
    assert curry not in state["facts"]
    assert idea["id"] not in state["ideas"]
    plan = state["plans"][plan["id"]]
    assert [e["recipe_id"] for e in plan["entries"]] == [chili]
    assert curry not in plan["recipe_snapshots"]
    assert curry not in plan["shopping_servings"]
    assert contents(unique_user, shopping.id) == ([400], {chili: 1})
    summary = api_client.get(f"{BASE}/plans/{plan['id']}/summary", headers=unique_user.token)
    assert summary.status_code == 200, summary.text

    # the week stays editable: removing the remaining dish works
    response = save(api_client, unique_user, monday, [])
    assert response.status_code == 200, response.text
    assert contents(unique_user, shopping.id) == ([], {})


def test_week_with_only_deleted_recipes_is_removed(api_client: TestClient, unique_user: TestUser):
    monday = next(WEEKS)
    food, unit = chicken(unique_user)
    curry = dish(api_client, unique_user, food, unit, 600)
    response = save(api_client, unique_user, monday, [entry(unique_user, curry, monday)])
    assert response.status_code == 200, response.text

    delete_recipe(api_client, unique_user, curry)

    plans = api_client.get(BASE, headers=unique_user.token).json()["state"]["plans"].values()
    assert not [p for p in plans if p["start"] == str(monday)]
    other = dish(api_client, unique_user, food, unit, 300)
    response = save(api_client, unique_user, monday, [entry(unique_user, other, monday)])
    assert response.status_code == 200, response.text


def test_stale_page_gets_a_clear_error(api_client: TestClient, unique_user: TestUser):
    """The week page still showed the deleted dish; saving was a 500 on PostgreSQL, now a hint to reload."""
    monday = next(WEEKS)
    food, unit = chicken(unique_user)
    curry = dish(api_client, unique_user, food, unit, 600)
    chili = dish(api_client, unique_user, food, unit, 400)
    entries = [entry(unique_user, curry, monday, "lunch"), entry(unique_user, chili, monday, "dinner")]
    assert save(api_client, unique_user, monday, entries).status_code == 200

    delete_recipe(api_client, unique_user, curry)
    response = save(api_client, unique_user, monday, [*entries, entry(unique_user, chili, monday, "breakfast")])

    assert response.status_code == 422, response.text
    assert "neu laden" in response.json()["detail"]
    # after reloading, the week only holds the chili and can be edited
    plan = next(
        p
        for p in api_client.get(BASE, headers=unique_user.token).json()["state"]["plans"].values()
        if p["start"] == str(monday)
    )
    response = save(api_client, unique_user, monday, [*plan["entries"], entry(unique_user, chili, monday, "breakfast")])
    assert response.status_code == 200, response.text
