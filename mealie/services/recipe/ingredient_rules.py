"""Fork rule: ingredient amounts live in structured fields, never in the note (see STRICT_INGREDIENTS)."""

import re

from mealie.core import exceptions
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient

# A note starting with a number or vulgar fraction carries an amount, e.g. "600 g Hähnchenbrust" or "½ Zwiebel".
_AMOUNT_IN_TEXT = re.compile(r"^\s*(\d|[¼½¾⅓⅔⅛])")


def ingredient_problems(ingredients: list[RecipeIngredient]) -> list[str]:
    problems: list[str] = []
    for n, ingredient in enumerate(ingredients, start=1):
        if ingredient.referenced_recipe:
            continue
        label = (ingredient.food.name if ingredient.food else "") or (ingredient.note or "").strip() or "leer"
        missing = []
        if not ingredient.quantity or ingredient.quantity <= 0:
            missing.append("Menge")
        if not ingredient.food or not ingredient.food.name.strip():
            missing.append("Lebensmittel")
        if missing:
            problems.append(f"Zutat {n} ({label}): {' und '.join(missing)} fehlt")
        if ingredient.note and _AMOUNT_IN_TEXT.match(ingredient.note):
            problems.append(f"Zutat {n} ({label}): Menge steht in der Notiz statt im Mengenfeld")
    return problems


def _key(i: RecipeIngredient) -> tuple:
    return (
        i.quantity or 0,
        i.unit.id if i.unit and getattr(i.unit, "id", None) else (i.unit.name if i.unit else None),
        i.food.id if i.food and getattr(i.food, "id", None) else (i.food.name if i.food else None),
        (i.note or "").strip(),
        i.referenced_recipe.id if i.referenced_recipe else None,
    )


def require_structured_ingredients(
    ingredients: list[RecipeIngredient], previous: list[RecipeIngredient] | None = None
) -> None:
    """Validate when the ingredient list changes; unrelated saves (image, assets) of old recipes stay possible."""
    if previous is not None and [_key(i) for i in ingredients] == [_key(i) for i in previous]:
        return
    if problems := ingredient_problems(ingredients):
        raise exceptions.InvalidIngredients(
            "Zutaten brauchen Menge und Lebensmittel als eigene Felder (Zutaten parsen). " + "; ".join(problems)
        )
