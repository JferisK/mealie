# ruff: noqa: E501, T201
"""Seed a local dev Mealie (localhost:9000) with realistic test data for UI QA.

Only for a throwaway dev database: uses the default dev admin and creates a
second test member. Run with `uv run python dev/qa/seed.py`.
"""

import io
import json
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta

from PIL import Image, ImageDraw

BASE = "http://localhost:9000/api"


def req(method, path, data=None, token=None, form=False, raw=None, ctype=None):
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if raw is not None:
        body, headers["Content-Type"] = raw, ctype
    elif form:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r) as resp:
            txt = resp.read().decode()
            return json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code}: {e.read().decode()[:400]}") from e


def login(user, pw):
    return req("POST", "/auth/token", {"username": user, "password": pw}, form=True)["access_token"]


admin = login("changeme@example.com", "MyPassword")
me = req("GET", "/users/self", token=admin)
req("PUT", f"/users/{me['id']}", {**me, "fullName": "Jakob", "username": "jakob"}, token=admin)

users = req("GET", "/admin/users?perPage=50", token=admin)["items"]
if not any(u["email"] == "sanja@example.test" for u in users):
    req(
        "POST",
        "/admin/users",
        {
            "username": "sanja",
            "fullName": "Sanja",
            "email": "sanja@example.test",
            "password": "SanjaTest123",
            "group": me["group"],
            "household": me["household"],
            "admin": False,
            "advanced": False,
            "canInvite": True,
            "canManage": True,
            "canManageHousehold": True,
            "canOrganize": True,
        },
        token=admin,
    )
sanja_token = login("sanja@example.test", "SanjaTest123")
sanja = req("GET", "/users/self", token=sanja_token)


def jpeg(color, label):
    img = Image.new("RGB", (1200, 800), color)
    d = ImageDraw.Draw(img)
    for i in range(0, 1200, 60):
        d.ellipse((i, 300 + (i % 180), i + 140, 440 + (i % 180)), fill=tuple(min(255, c + 30) for c in color))
    d.text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return buf.getvalue()


RECIPES = [
    {
        "name": "Thunfisch-Kichererbsen-Salat",
        "desc": "Schneller, eiweißreicher Salat mit Thunfisch, Kichererbsen, Gurke und Zitronen-Dressing. Ideal zum Mitnehmen.",
        "total": "20 Minuten",
        "prep": "15 Minuten",
        "perform": "5 Minuten",
        "servings": 2,
        "kcal": 480,
        "protein": 42,
        "color": (66, 120, 98),
        "image": True,
        "ingredients": [
            "1 Dose Thunfisch im eigenen Saft",
            "1 Dose Kichererbsen",
            "1 Salatgurke",
            "1 rote Zwiebel",
            "1 Zitrone",
            "2 EL Olivenöl",
            "Salz, Pfeffer",
        ],
        "steps": [
            "Kichererbsen abgießen und abspülen.",
            "Gurke und Zwiebel klein schneiden.",
            "Thunfisch abtropfen lassen und alles vermengen.",
            "Mit Zitronensaft, Öl, Salz und Pfeffer abschmecken.",
        ],
    },
    {
        "name": "Hähnchen-Gemüse-Curry mit Basmati und extra viel frischem Koriander",
        "desc": "Cremiges, mildes Curry mit Hähnchenbrust, Paprika, Zucchini und leichter Kokosmilch.",
        "total": "45 Minuten",
        "prep": "15 Minuten",
        "perform": "30 Minuten",
        "servings": 4,
        "kcal": 610,
        "protein": 48,
        "color": (190, 120, 40),
        "image": True,
        "ingredients": [
            "600 g Hähnchenbrust",
            "2 Paprika",
            "1 Zucchini",
            "400 ml leichte Kokosmilch",
            "2 EL rote Currypaste",
            "250 g Basmatireis",
            "1 Bund Koriander",
        ],
        "steps": [
            "Reis nach Packungsanweisung kochen.",
            "Hähnchen würfeln und scharf anbraten.",
            "Gemüse zugeben und 5 Minuten mitbraten.",
            "Currypaste und Kokosmilch einrühren, 15 Minuten köcheln.",
            "Mit Koriander servieren.",
        ],
    },
    {
        "name": "Overnight Oats mit Beeren",
        "desc": "Vorbereitetes Frühstück mit Skyr, Haferflocken und Beeren.",
        "total": "5 Minuten",
        "prep": "5 Minuten",
        "perform": None,
        "servings": 1,
        "kcal": 390,
        "protein": 30,
        "color": (140, 70, 110),
        "image": False,
        "ingredients": ["50 g Haferflocken", "150 g Skyr", "100 ml Milch", "80 g Beeren"],
        "steps": ["Alles verrühren und über Nacht kühl stellen."],
    },
    {
        "name": "Linsen-Bolognese",
        "desc": "",
        "total": "40 Minuten",
        "prep": "10 Minuten",
        "perform": "30 Minuten",
        "servings": 4,
        "kcal": 560,
        "protein": 32,
        "color": (150, 60, 40),
        "image": True,
        "ingredients": [
            "250 g rote Linsen",
            "1 Dose gehackte Tomaten",
            "2 Karotten",
            "1 Zwiebel",
            "400 g Vollkornspaghetti",
        ],
        "steps": [
            "Gemüse fein würfeln und anschwitzen.",
            "Linsen und Tomaten zugeben, 20 Minuten köcheln.",
            "Mit Spaghetti servieren.",
        ],
    },
    {
        "name": "Rührei mit Spinat",
        "desc": "Proteinreiches Frühstück in 10 Minuten.",
        "total": "10 Minuten",
        "prep": None,
        "perform": "10 Minuten",
        "servings": 1,
        "kcal": 320,
        "protein": 26,
        "color": (200, 170, 60),
        "image": False,
        "ingredients": ["3 Eier", "100 g Spinat", "1 TL Butter"],
        "steps": ["Spinat in Butter zusammenfallen lassen.", "Eier verquirlen, zugeben und stocken lassen."],
    },
]

today = date(2026, 10, 16)
monday = today - timedelta(days=today.weekday())
ids = {}
existing = {r["name"]: r for r in req("GET", "/recipes?perPage=100", token=admin)["items"]}
for i, r in enumerate(RECIPES):
    slug = (
        existing[r["name"]]["slug"]
        if r["name"] in existing
        else req("POST", "/recipes", {"name": r["name"]}, token=admin)
    )
    full = req("GET", f"/recipes/{slug}", token=admin)
    patch = {
        "description": r["desc"],
        "totalTime": r["total"],
        "prepTime": r["prep"],
        "performTime": r["perform"],
        "recipeServings": r["servings"],
        "recipeYieldQuantity": 0,
        "recipeYield": "",
        "recipeIngredient": [
            {
                "note": t,
                "display": t,
                "quantity": 0,
                "disableAmount": True,
                "referenceId": f"00000000-0000-4000-8000-00000000{i}{j:03d}",
            }
            for j, t in enumerate(r["ingredients"])
        ],
        "recipeInstructions": [
            {
                "id": f"00000000-0000-4000-9000-00000000{i}{j:03d}",
                "title": "",
                "summary": "",
                "text": t,
                "ingredientReferences": [],
            }
            for j, t in enumerate(r["steps"])
        ],
        "nutrition": {"calories": str(r["kcal"]), "proteinContent": str(r["protein"])},
        "tags": [],
        "recipeCategory": [],
        "tools": [],
    }
    req("PATCH", f"/recipes/{slug}", patch, token=admin)
    if r["image"] and not full.get("image"):
        boundary = "----seedboundary"
        img = jpeg(r["color"], r["name"])
        body = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="extension"\r\n\r\njpg\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="img.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
            ).encode()
            + img
            + f"\r\n--{boundary}--\r\n".encode()
        )
        req("PUT", f"/recipes/{slug}/image", raw=body, ctype=f"multipart/form-data; boundary={boundary}", token=admin)
    if i == 0:
        req(
            "PATCH",
            f"/recipes/{slug}/last-made",
            {"timestamp": datetime(2026, 10, 10, 12, tzinfo=UTC).isoformat()},
            token=admin,
        )
        req("POST", f"/users/{me['id']}/ratings/{slug}", {"rating": 4, "isFavorite": True}, token=admin)
    ids[r["name"]] = req("GET", f"/recipes/{slug}", token=admin)["id"]

state = req("GET", "/households/planning", token=admin)
rev = state["revision"]
for r in RECIPES:
    grams = 300
    out = req(
        "PUT",
        f"/households/planning/recipe-facts?revision={rev}",
        {
            "recipe_id": ids[r["name"]],
            "servings": r["servings"],
            "ingredients": [
                {
                    "name": "Gesamt",
                    "grams": grams * r["servings"],
                    "per_100g": {
                        "calories": r["kcal"] / 3,
                        "protein": r["protein"] / 3,
                        "carbohydrate": 12,
                        "fat": 6,
                        "fiber": 3,
                    },
                    "source": "Testdaten",
                }
            ],
            "gluten_free": "yes" if "Salat" in r["name"] else "unknown",
            "lactose_free": "no" if "Oats" in r["name"] else "yes",
            "freezer_friendly": "yes" if r["name"].startswith(("Hähnchen", "Linsen")) else "no",
            "evidence": "Zutatenliste geprüft (Testdaten)",
        },
        token=admin,
    )
    rev = out["revision"]

salad, curry, oats, bolo, egg = (ids[r["name"]] for r in RECIPES)
if not any(b["recipe_id"] == bolo for b in out["state"]["batches"].values()):
    out = req(
        "POST",
        f"/households/planning/batches?revision={rev}",
        {"recipe_id": bolo, "servings": 3, "frozen_on": "2026-10-01", "location": "Gefrierschrank oben"},
        token=admin,
    )
    rev = out["revision"]
    out = req(
        "POST",
        f"/households/planning/batches?revision={rev}",
        {"recipe_id": curry, "servings": 2, "frozen_on": "2026-09-20", "location": ""},
        token=admin,
    )
    rev = out["revision"]


def e(user, recipe, d, meal):
    return {
        "user_id": user,
        "recipe_id": recipe,
        "day": (monday + timedelta(days=d)).isoformat(),
        "meal": meal,
        "servings": 1,
    }


J, S = me["id"], sanja["id"]
entries = []
for d in range(5):
    entries += [e(J, oats, d, "breakfast")]
for d in (0, 2):
    entries += [e(J, curry, d, "dinner"), e(S, curry, d, "dinner")]
entries += [
    e(J, salad, 1, "lunch"),
    e(S, salad, 1, "lunch"),
    e(J, salad, 3, "lunch"),
    e(J, bolo, 4, "dinner"),
    e(S, egg, 4, "dinner"),
    e(S, egg, 5, "breakfast"),
]
out = req(
    "PUT",
    f"/households/planning/weeks/{monday.isoformat()}?revision={rev}",
    {"start": monday.isoformat(), "entries": entries},
    token=admin,
)
rev = out["revision"]

if not out["state"]["ideas"]:
    out = req(
        "POST",
        f"/households/planning/ideas?revision={rev}",
        {
            "week_start": (monday + timedelta(days=7)).isoformat(),
            "recipe_id": curry,
            "note": "Hätte mal wieder Lust auf Curry",
        },
        token=admin,
    )
    rev = out["revision"]
    out = req(
        "POST",
        f"/households/planning/ideas?revision={rev}",
        {"week_start": (monday + timedelta(days=7)).isoformat(), "recipe_id": salad},
        token=sanja_token,
    )
    rev = out["revision"]

personal = req("GET", "/households/planning/me", token=admin)
p = req(
    "PUT",
    f"/households/planning/me/profile?revision={personal['revision']}",
    {
        "birth_date": "1994-04-04",
        "height_cm": 182,
        "equation_sex": "male",
        "activity_factor": 1.375,
        "deficit_kcal": 400,
        "protein_reference_kg": 80,
        "protein_g_per_kg": 1.6,
    },
    token=admin,
)
p = req(
    "POST",
    f"/households/planning/me/health?revision={p['revision']}",
    {
        "observations": [
            {
                "id": f"manual:{(today - timedelta(days=k)).isoformat()}",
                "kind": "weight_kg",
                "value": 88.4 - k * 0.1,
                "at": f"{(today - timedelta(days=k)).isoformat()}T07:00:00+00:00",
                "source": "manual",
            }
            for k in range(3)
        ]
    },
    token=admin,
)
p = req("POST", f"/households/planning/me/goals/propose?revision={p['revision']}", token=admin)
req(
    "POST",
    f"/households/planning/me/goals/{p['state']['revisions'][-1]['id']}/confirm?revision={p['revision']}",
    token=admin,
)
print("seeded", monday, list(ids))
