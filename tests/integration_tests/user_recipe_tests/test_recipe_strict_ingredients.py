"""STRICT_INGREDIENTS: amounts live in quantity/unit/food fields, never in the note."""

import pytest
from fastapi.testclient import TestClient

from mealie.core.config import get_app_settings
from mealie.schema.recipe.recipe import Recipe
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient, SaveIngredientFood
from mealie.services.recipe.ingredient_rules import ingredient_problems
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


@pytest.fixture
def strict(monkeypatch):
    monkeypatch.setattr(get_app_settings(), "STRICT_INGREDIENTS", True)


def unparsed_recipe(user: TestUser) -> Recipe:
    return user.repos.recipes.create(
        Recipe(
            user_id=user.user_id,
            group_id=user.group_id,
            name=random_string(10),
            recipe_ingredient=[RecipeIngredient(quantity=0, note="600 g Hähnchenbrust")],
        )
    )


def structured(user: TestUser, quantity: float = 600, note: str = "") -> dict:
    food = user.repos.ingredient_foods.create(SaveIngredientFood(name=random_string(8), group_id=user.group_id))
    return {"quantity": quantity, "food": food.model_dump(mode="json"), "note": note}


def test_rules_name_each_problem():
    assert ingredient_problems([RecipeIngredient(quantity=0, note="600 g Huhn")]) == [
        "Zutat 1 (600 g Huhn): Menge und Lebensmittel fehlt",
        "Zutat 1 (600 g Huhn): Menge steht in der Notiz statt im Mengenfeld",
    ]
    assert ingredient_problems([RecipeIngredient(quantity=1, note="½ Zwiebel")])[-1].endswith("statt im Mengenfeld")


def test_patch_rejects_amount_in_text(api_client: TestClient, unique_user: TestUser, strict):
    recipe = unparsed_recipe(unique_user)
    body = {"recipeIngredient": [{"quantity": 0, "note": "400 g Hähnchenbrust"}]}
    response = api_client.patch(api_routes.recipes_slug(recipe.slug), json=body, headers=unique_user.token)
    assert response.status_code == 422
    assert "Menge" in response.json()["detail"]["message"]
    stored = unique_user.repos.recipes.get_one(recipe.slug)
    assert [i.note for i in stored.recipe_ingredient] == ["600 g Hähnchenbrust"]


def test_patch_accepts_structured_ingredients(api_client: TestClient, unique_user: TestUser, strict):
    recipe = unparsed_recipe(unique_user)
    body = {"recipeIngredient": [structured(unique_user, note="gewürfelt")]}
    response = api_client.patch(api_routes.recipes_slug(recipe.slug), json=body, headers=unique_user.token)
    assert response.status_code == 200, response.text
    assert response.json()["recipeIngredient"][0]["quantity"] == 600


def test_put_rejects_missing_food(api_client: TestClient, unique_user: TestUser, strict):
    recipe = unparsed_recipe(unique_user)
    data = api_client.get(api_routes.recipes_slug(recipe.slug), headers=unique_user.token).json()
    data["recipeIngredient"] = [{"quantity": 2, "note": "Eier"}]
    response = api_client.put(api_routes.recipes_slug(recipe.slug), json=data, headers=unique_user.token)
    assert response.status_code == 422
    assert "Lebensmittel fehlt" in response.json()["detail"]["message"]


def test_unrelated_saves_of_old_recipes_still_work(api_client: TestClient, unique_user: TestUser, strict):
    recipe = unparsed_recipe(unique_user)
    patch = {"description": "neu"}
    assert (
        api_client.patch(api_routes.recipes_slug(recipe.slug), json=patch, headers=unique_user.token).status_code == 200
    )
    data = api_client.get(api_routes.recipes_slug(recipe.slug), headers=unique_user.token).json()
    data["description"] = "auch per PUT"
    assert api_client.put(api_routes.recipes_slug(recipe.slug), json=data, headers=unique_user.token).status_code == 200


def test_default_off_keeps_upstream_behaviour(api_client: TestClient, unique_user: TestUser):
    recipe = unparsed_recipe(unique_user)
    body = {"recipeIngredient": [{"quantity": 0, "note": "400 g Hähnchenbrust"}]}
    assert (
        api_client.patch(api_routes.recipes_slug(recipe.slug), json=body, headers=unique_user.token).status_code == 200
    )


def test_planner_facts_require_parsed_recipe(api_client: TestClient, unique_user: TestUser, strict):
    recipe = unparsed_recipe(unique_user)
    revision = api_client.get("/api/households/planning", headers=unique_user.token).json()["revision"]
    facts = {"recipe_id": str(recipe.id), "servings": 4, "ingredients": []}
    response = api_client.put(
        f"/api/households/planning/recipe-facts?revision={revision}", json=facts, headers=unique_user.token
    )
    assert response.status_code == 422
    assert "parsen" in response.json()["detail"]
