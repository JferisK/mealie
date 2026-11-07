"""Default shopping-list category order that follows a typical supermarket walk.

Fresh produce first, then bakery, meat/fish, dairy, frozen ("TK") and the dry goods;
household and "other" come last. Unknown (custom) categories land between the known
ones and the tail, alphabetically. The frontend mirrors these rules in
``frontend/app/lib/shopping/label-order.ts``.
"""

import re

FROZEN_LABEL_NAME = "TK"

# (tier, pattern) -- the first matching pattern wins, so specific rules come first.
_RULES: list[tuple[int, re.Pattern[str]]] = [
    (40, re.compile(r"\btk\b|tiefk[üu]e?h?l|frozen")),
    (60, re.compile(r"gew[üu]e?rz|spice|condiment|w[üu]rzmittel|\bö?oils?\b|\böl\b|baking|backzut|backen")),
    (10, re.compile(r"obst|gem[üu]e?se|produce|fruit|vegetable")),
    (20, re.compile(r"brot|back|bakery|baked")),
    (30, re.compile(r"fleisch|wurst|fisch|meeresfr|meat|seafood|fish")),
    (35, re.compile(r"milch|k[äa]e?se|dairy|cheese|eier|\begg")),
    (50, re.compile(r"getreide|nudel|reis|konserv|canned|grain|pasta|rice")),
    (70, re.compile(r"s[üu]e?[ßs]|snack|sweet")),
    (80, re.compile(r"getr[äa]e?nk|beverage|drink|alkohol|alcohol")),
    (95, re.compile(r"haushalt|household|sonstig|other|bio|health")),
]
_UNKNOWN_TIER = 90


def is_frozen_label(name: str) -> bool:
    return bool(_RULES[0][1].search(name.lower()))


def supermarket_rank(name: str) -> int:
    lowered = name.lower()
    for tier, pattern in _RULES:
        if pattern.search(lowered):
            return tier
    return _UNKNOWN_TIER


def supermarket_sort_key(name: str) -> tuple[int, str]:
    return supermarket_rank(name), name.lower()
