"""Pure calculations: unknown values never become zero or inferred nutrition."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import mean

from mealie.schema.household_planner.models import (
    GoalRevision,
    GoalsIn,
    Nutrients,
    PersonalState,
    PlanIn,
    PlannerState,
    PlanOut,
    RecipeFactsIn,
)


def nutrition(facts: RecipeFactsIn) -> tuple[Nutrients, float]:
    values: dict[str, float | None] = {}
    for key in Nutrients.model_fields:
        complete = bool(facts.ingredients) and all(
            i.source.strip() and getattr(i.per_100g, key) is not None for i in facts.ingredients
        )
        values[key] = (
            round(sum(getattr(i.per_100g, key) * i.grams / 100 for i in facts.ingredients) / facts.servings, 2)
            if complete
            else None
        )
    total = sum(i.grams for i in facts.ingredients)
    covered = sum(i.grams for i in facts.ingredients if i.source.strip() and i.per_100g.calories is not None)
    return Nutrients(**values), round(covered / total, 3) if total else 0


def reserved(state: PlannerState, batch_id: str, exclude_plan: str | None = None) -> float:
    return sum(
        e.servings
        for k, p in state.plans.items()
        if k != exclude_plan
        for e in p.entries
        if str(e.batch_id) == batch_id and e.id not in p.consumed
    )


def plan_summary(plan: PlanIn, state: PlannerState) -> dict:
    days: dict[str, dict] = {}
    cooking: dict[str, dict] = {}
    shopping: dict[str, dict] = {}
    for e in plan.entries:
        snapshots = plan.recipe_snapshots if isinstance(plan, PlanOut) else {}
        facts = (
            state.batches[str(e.batch_id)].facts
            if e.batch_id
            else snapshots.get(str(e.recipe_id), state.facts.get(str(e.recipe_id)))
        )
        if facts is None:
            raise ValueError("Missing recipe facts")
        key = f"{e.day}:{e.user_id}"
        day = days.setdefault(
            key,
            {
                "day": str(e.day),
                "user_id": str(e.user_id),
                "entries": 0,
                "known_entries": 0,
                "nutrients": dict.fromkeys(Nutrients.model_fields, 0.0),
            },
        )
        day["entries"] += 1
        day["known_entries"] += facts.per_serving.calories is not None
        for nutrient in Nutrients.model_fields:
            value = getattr(facts.per_serving, nutrient)
            if value is None:
                day["nutrients"][nutrient] = None
            elif day["nutrients"][nutrient] is not None:
                day["nutrients"][nutrient] += value * e.servings
        if e.batch_id:
            continue
        cook = cooking.setdefault(
            str(e.recipe_id), {"recipe_id": str(e.recipe_id), "name": facts.name, "servings": 0.0}
        )
        cook["servings"] += e.servings
        for i in facts.ingredients:
            # State is part of identity: cooked rice and dry rice cannot be merged.
            identity = f"{i.name.strip().casefold()}|{i.state}"
            item = shopping.setdefault(
                identity, {"id": identity, "name": i.name, "state": i.state, "grams": 0.0, "recipe_ids": []}
            )
            item["grams"] += i.grams * e.servings / facts.servings
            if str(e.recipe_id) not in item["recipe_ids"]:
                item["recipe_ids"].append(str(e.recipe_id))
    for item in shopping.values():
        item["grams"] = round(item["grams"], 1)
    for day in days.values():
        day["nutrients"] = {k: round(v, 1) if v is not None else None for k, v in day["nutrients"].items()}
    return {
        "days": list(days.values()),
        "cooking": list(cooking.values()),
        "shopping": list(shopping.values()),
        "notice": (
            "Planned meals only; a partial day is not a complete intake record. "
            "Ingredient amounts use the stated preparation state."
        ),
    }


# "600 g Hähnchenbrust" -> "Hähnchenbrust"; only metric weights/volumes that facts store as grams.
_LEADING_AMOUNT = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l)\s+", re.IGNORECASE)


@dataclass(frozen=True)
class NativeLine:
    """A native recipe ingredient. Structured lines carry food and amount per serving."""

    text: str
    food: str | None = None
    food_id: str | None = None
    unit_id: str | None = None
    per_serving: float = 0


def week_shopping_items(
    plan: PlanIn, state: PlannerState, native_lines: dict[str, list[NativeLine]]
) -> tuple[list[dict], list[dict]]:
    """Purchases for freshly cooked meals: summed grams per ingredient, plus native lines without facts.

    Raw and as-sold amounts are both bought as-is and merge; cooked amounts stay separate.
    Uncovered structured lines (e.g. 2 EL Currypulver) are scaled to the planned servings; the native list
    merges equal foods. Unstructured lines (old free text) cannot be scaled, so each text is listed once.
    """
    summary = plan_summary(plan, state)
    items: dict[str, dict] = {}
    for s in summary["shopping"]:
        cooked = s["state"] == "cooked"
        name = s["name"].strip() + (" (gekocht)" if cooked else "")
        item = items.setdefault(
            f"{s['name'].strip().casefold()}|{cooked}", {"name": name, "grams": 0.0, "recipe_ids": []}
        )
        item["grams"] = round(item["grams"] + s["grams"], 1)
        item["recipe_ids"] += [r for r in s["recipe_ids"] if r not in item["recipe_ids"]]

    servings = {c["recipe_id"]: c["servings"] for c in summary["cooking"]}
    extras: list[dict] = []
    texts: set[str] = set()
    snapshots = plan.recipe_snapshots if isinstance(plan, PlanOut) else {}
    for recipe_id in dict.fromkeys(str(e.recipe_id) for e in plan.entries if not e.batch_id):
        facts = snapshots.get(recipe_id, state.facts.get(recipe_id))
        covered = {i.name.strip().casefold() for i in facts.ingredients} if facts else set()
        for line in native_lines.get(recipe_id, []):
            text = line.text.strip()
            name = (line.food or _LEADING_AMOUNT.sub("", text)).strip().casefold()
            if not (text or line.food) or name in covered:
                continue
            if line.food_id and line.per_serving > 0:
                extras.append(
                    {
                        "food_id": line.food_id,
                        "unit_id": line.unit_id,
                        "quantity": round(line.per_serving * servings.get(recipe_id, 0), 2),
                        "recipe_id": recipe_id,
                    }
                )
            elif text.casefold() not in texts:
                texts.add(text.casefold())
                extras.append({"note": text})
    return list(items.values()), extras


def monthly_proposal(state: PersonalState, today: date | None = None) -> GoalRevision:
    today = today or datetime.now(UTC).date()
    p = state.profile
    if not p.birth_date or not p.height_cm or not p.equation_sex or not p.protein_reference_kg:
        raise ValueError("Bitte Geburtsdatum, Größe, Formel-Geschlecht und Protein-Referenzgewicht eintragen.")
    age = today.year - p.birth_date.year - ((today.month, today.day) < (p.birth_date.month, p.birth_date.day))
    if age < 18:
        raise ValueError("Die Formeln gelten nur für Erwachsene.")
    # One daily mean avoids overweighting days with multiple scale readings.
    weights: dict[date, list[float]] = {}
    for o in state.observations.values():
        if o.kind == "weight_kg" and today - timedelta(days=27) <= o.at.date() <= today:
            weights.setdefault(o.at.date(), []).append(o.value)
    recent = [mean(v) for d, v in weights.items() if d >= today - timedelta(days=6)]
    fallback = sorted((d, mean(v)) for d, v in weights.items() if d >= today - timedelta(days=13))
    if not recent and not fallback:
        raise ValueError("Bitte ein aktuelles Gewicht eintragen (Messung aus den letzten 14 Tagen).")
    weight = mean(recent) if recent else fallback[-1][1]
    days_used = len(recent) if recent else 1
    # Mifflin et al. 1990, PMID 2305711. Harris-Benedict original comparison, not an averaged prescription.
    msj = 10 * weight + 6.25 * p.height_cm - 5 * age + (5 if p.equation_sex == "male" else -161)
    hb = (
        (66.473 + 13.7516 * weight + 5.0033 * p.height_cm - 6.755 * age)
        if p.equation_sex == "male"
        else (655.0955 + 9.5634 * weight + 1.8496 * p.height_cm - 4.6756 * age)
    )
    energy = msj * p.activity_factor - p.deficit_kcal
    old = [mean(v) for d, v in weights.items() if d <= today - timedelta(days=21)]
    trend = (
        f" Gewichtsmittel {weight - mean(old):+.1f} kg gegenüber vor drei Wochen."
        if len(old) >= 3
        else " Für einen Vier-Wochen-Vergleich fehlen noch Messwerte."
    )
    if days_used < 3:
        trend += f" Berechnet aus {days_used} Messtag(en); mit mehr Messungen wird der Wert stabiler."
    return GoalRevision(
        created_at=datetime.now(UTC),
        goals=GoalsIn(calories=round(energy), protein=round(p.protein_reference_kg * p.protein_g_per_kg)),
        explanation=(
            "Grundumsatz nach Mifflin-St Jeor × gewählter Aktivitätsfaktor − vereinbartes Defizit. "
            "Trainingskalorien werden nicht zusätzlich addiert; die Formel ist eine Schätzung, keine Messung. "
            "Protein = Referenzgewicht × gewählter Faktor."
        )
        + trend,
        inputs={
            "formula": "mifflin-st-jeor-1990-v1",
            "weight_kg": round(weight, 2),
            "height_cm": p.height_cm,
            "age": age,
            "equation_sex": p.equation_sex,
            "resting_kcal": round(msj),
            "harris_benedict_1919_comparison": round(hb),
            "activity_factor": p.activity_factor,
            "deficit_kcal": p.deficit_kcal,
            "protein_reference_kg": p.protein_reference_kg,
            "protein_g_per_kg": p.protein_g_per_kg,
        },
    )
