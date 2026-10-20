"""Planner shows the recipe as it is now: name, slug and image follow later recipe edits."""

from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from mealie.schema.recipe.recipe import Recipe
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser

BASE = "/api/households/planning"


def state(api_client: TestClient, user: TestUser) -> dict:
    return api_client.get(BASE, headers=user.token).json()


def png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def test_planner_follows_recipe_image_and_name(api_client: TestClient, unique_user: TestUser):
    recipe = unique_user.repos.recipes.create(
        Recipe(user_id=unique_user.user_id, group_id=unique_user.group_id, name=random_string(10), recipe_servings=1)
    )
    rid = str(recipe.id)
    facts = {"recipe_id": rid, "servings": 1, "ingredients": [{"name": "Skyr", "grams": 250}]}
    rev = state(api_client, unique_user)["revision"]
    assert (
        api_client.put(f"{BASE}/recipe-facts?revision={rev}", json=facts, headers=unique_user.token).status_code == 200
    )
    rev = state(api_client, unique_user)["revision"]
    idea = {"id": str(uuid4()), "week_start": "2026-11-02", "recipe_id": rid}
    assert api_client.post(f"{BASE}/ideas?revision={rev}", json=idea, headers=unique_user.token).status_code == 200
    assert state(api_client, unique_user)["state"]["facts"][rid]["image"] is None

    # photo added after the facts, then replaced, then the recipe renamed
    images = []
    for _ in range(2):
        response = api_client.put(
            api_routes.recipes_slug_image(recipe.slug),
            files={"image": ("bowl.png", png(), "image/png")},
            data={"extension": "png"},
            headers=unique_user.token,
        )
        assert response.status_code == 200, response.text
        images.append(response.json()["image"])
        assert state(api_client, unique_user)["state"]["facts"][rid]["image"] == images[-1]
    assert images[0] != images[1]

    new_name = random_string(12)
    response = api_client.patch(
        api_routes.recipes_slug(recipe.slug), json={"name": new_name}, headers=unique_user.token
    )
    assert response.status_code == 200, response.text
    new_slug = response.json()["slug"]

    current = state(api_client, unique_user)["state"]
    assert (current["facts"][rid]["name"], current["facts"][rid]["slug"]) == (new_name, new_slug)
    idea_out = current["ideas"][idea["id"]]
    assert (idea_out["name"], idea_out["slug"], idea_out["image"]) == (new_name, new_slug, images[-1])
    plan_entry = {
        "user_id": str(unique_user.user_id),
        "recipe_id": rid,
        "day": "2026-11-02",
        "meal": "lunch",
        "servings": 1,
    }
    rev = state(api_client, unique_user)["revision"]
    saved = api_client.put(
        f"{BASE}/weeks/2026-11-02?revision={rev}",
        json={"start": "2026-11-02", "entries": [{"id": str(uuid4()), **plan_entry}]},
        headers=unique_user.token,
    ).json()
    plan_id = next(p["id"] for p in saved["state"]["plans"].values() if p["start"] == "2026-11-02")
    summary = api_client.get(f"{BASE}/plans/{plan_id}/summary", headers=unique_user.token).json()
    assert summary["cooking"][0]["name"] == new_name
