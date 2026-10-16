// Household members as they appear across the planner: a stable colour per
// person and the shortest name prefix that is still unique ("J" and "S", or
// "Jak" and "Jas" when two names start alike).

export interface PlannerMember {
  id: string;
  name: string;
  meal_preferences?: { gluten_free?: boolean; lactose_free?: boolean; avoid_traces?: boolean };
}

export interface PlannerPerson extends PlannerMember {
  label: string;
  color: string;
}

const PERSON_COLORS = 6;

export function shortLabel(name: string, others: string[]): string {
  const clean = (name.trim() || "?").toLocaleLowerCase();
  const rest = others.map(o => o.trim().toLocaleLowerCase());
  const capital = (s: string) => s.charAt(0).toLocaleUpperCase() + s.slice(1);
  for (let n = 1; n <= Math.min(3, clean.length); n++) {
    const prefix = clean.slice(0, n);
    if (!rest.some(o => o.startsWith(prefix))) return capital(prefix);
  }
  return capital(clean.slice(0, 2));
}

export function toPeople(members: PlannerMember[]): PlannerPerson[] {
  const names = members.map(m => m.name || "");
  const seen = new Map<string, number>();
  return members.map((m, i) => {
    let label = shortLabel(names[i]!, names.filter((_, j) => j !== i));
    const count = (seen.get(label) || 0) + 1;
    seen.set(label, count);
    if (count > 1) label = `${label}${count}`;
    return { ...m, label, color: `var(--fork-person-${(i % PERSON_COLORS) + 1})` };
  });
}
