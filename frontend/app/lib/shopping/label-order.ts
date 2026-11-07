// Mirrors mealie/services/household_services/label_order.py: the default category
// order follows a typical supermarket walk (produce first, frozen "TK" in the middle).
const RULES: [number, RegExp][] = [
  [40, /\btk\b|tiefk[üu]e?h?l|frozen/],
  [60, /gew[üu]e?rz|spice|condiment|w[üu]rzmittel|\bö?oils?\b|\böl\b|baking|backzut|backen/],
  [10, /obst|gem[üu]e?se|produce|fruit|vegetable/],
  [20, /brot|back|bakery|baked/],
  [30, /fleisch|wurst|fisch|meeresfr|meat|seafood|fish/],
  [35, /milch|k[äa]e?se|dairy|cheese|eier|\begg/],
  [50, /getreide|nudel|reis|konserv|canned|grain|pasta|rice/],
  [70, /s[üu]e?[ßs]|snack|sweet/],
  [80, /getr[äa]e?nk|beverage|drink|alkohol|alcohol/],
  [95, /haushalt|household|sonstig|other|bio|health/],
];
const UNKNOWN_TIER = 90;

export function supermarketRank(name: string): number {
  const lowered = name.toLowerCase();
  return RULES.find(([, pattern]) => pattern.test(lowered))?.[0] ?? UNKNOWN_TIER;
}

export function sortBySupermarket<T>(items: T[], nameOf: (item: T) => string): T[] {
  return [...items].sort((a, b) => supermarketRank(nameOf(a)) - supermarketRank(nameOf(b)) || nameOf(a).toLowerCase().localeCompare(nameOf(b).toLowerCase()));
}
