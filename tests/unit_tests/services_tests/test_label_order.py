from mealie.services.household_services.label_order import is_frozen_label, supermarket_sort_key


def test_supermarket_order_german_seed_labels():
    names = [
        "Alkohol", "Backwaren", "Baking", "Bio-Lebensmittel", "Fleisch", "Getränke", "Getreide", "Gewürze",
        "Haushalt", "Konserven", "Milchprodukte", "Obst & Gemüse", "Sonstiges", "Süßigkeiten", "Tiefkühlware",
    ]  # fmt: skip
    ordered = sorted(names, key=supermarket_sort_key)
    assert ordered[0] == "Obst & Gemüse"
    assert ordered.index("Backwaren") < ordered.index("Fleisch") < ordered.index("Milchprodukte")
    assert ordered.index("Milchprodukte") < ordered.index("Tiefkühlware") < ordered.index("Konserven")
    assert ordered.index("Baking") > ordered.index("Konserven")
    assert ordered[-2:] == ["Bio-Lebensmittel", "Haushalt"] or ordered[-1] in {"Sonstiges", "Haushalt"}


def test_frozen_label_detection():
    assert is_frozen_label("TK")
    assert is_frozen_label("Tiefkühlware")
    assert is_frozen_label("Frozen Foods")
    assert not is_frozen_label("Obst & Gemüse")


def test_unknown_label_sits_before_the_tail():
    ordered = sorted(["Haushalt", "Zeitschriften", "Obst & Gemüse"], key=supermarket_sort_key)
    assert ordered == ["Obst & Gemüse", "Zeitschriften", "Haushalt"]
