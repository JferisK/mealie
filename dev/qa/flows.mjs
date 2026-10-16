// Usage: node dev/qa/flows.mjs [baseUrl]
// Functional smoke test of the planner flows through the UI (WebKit, 390px).
// Verifies results through the API. Run against the seeded local dev stack only.
import { webkit } from "playwright";

const BASE = process.argv[2] || "http://localhost:3000";
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log(`${ok ? "✓" : "✗"} ${name}${detail ? ` – ${detail}` : ""}`); };

const browser = await webkit.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: "de-DE" });
await ctx.addCookies([{ name: "i18n_redirected", value: "de-DE", url: BASE }]);
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", e => errors.push(e.message));
await page.goto(`${BASE}/login`);
await page.locator("input[type=text], input[type=email]").first().fill(process.env.QA_USER || "changeme@example.com");
await page.locator("input[type=password]").fill(process.env.QA_PASSWORD || "MyPassword");
await page.locator("button[type=submit]").click();
await page.waitForURL(u => !u.pathname.startsWith("/login"));
const api = async (path, init) => page.evaluate(async ([p, i]) => (await fetch(p, { credentials: "include", ...i })).json(), [path, init]);
const settle = async () => { await page.waitForLoadState("networkidle").catch(() => {}); await page.waitForTimeout(700); };
const planFor = async (start) => Object.values((await api("/api/households/planning")).state.plans).find(p => p.start === start);
const week = (await api("/api/households/planning")).state.plans && Object.values((await api("/api/households/planning")).state.plans)[0]?.start;

// 1. Plan a dish into an empty slot (Sunday breakfast) and remove it again.
await page.goto(`${BASE}/household/portions?week=${week}`);
await settle();
const before = (await planFor(week)).entries.length;
await page.locator(".pw-day").last().locator(".pw-empty").first().click();
await page.waitForTimeout(500);
await page.locator(".pw-pick").filter({ hasText: "Rührei" }).click();
await page.waitForTimeout(400);
const preselected = await page.locator(".pw-chip[aria-pressed=true]").count();
await page.getByRole("button", { name: "Speichern" }).click();
await settle();
const afterAdd = (await planFor(week)).entries.length;
check("plan dish into empty slot", afterAdd === before + preselected && preselected > 0, `${before} → ${afterAdd} entries, ${preselected} preselected`);
await page.locator(".pw-day").last().locator(".pw-dish").filter({ hasText: "Rührei" }).click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: /Aus der Woche entfernen/ }).click();
await settle();
const afterRemove = (await planFor(week)).entries.filter(e => e.day.endsWith(String(Number(week.slice(8)) + 6).padStart(2, "0"))).length;
check("remove dish from week", (await planFor(week)).entries.length < afterAdd, `sunday entries now ${afterRemove}`);

// 2. Week plan → shopping list, creating the list inline when none exists.
const listsBefore = (await api("/api/households/shopping/lists?perPage=-1")).items.length;
await page.getByRole("button", { name: /Einkaufsliste erstellen/ }).click();
await page.waitForTimeout(1200);
if (!listsBefore) {
  await page.getByRole("button", { name: "Erstellen", exact: true }).click();
  await page.waitForTimeout(1500);
}
await page.getByRole("button", { name: /^Hinzufügen$|Zur Einkaufsliste hinzufügen/ }).last().click();
await settle();
const lists = (await api("/api/households/shopping/lists?perPage=-1")).items;
const items = lists.length ? (await api(`/api/households/shopping/lists/${lists[0].id}`)).listItems.length : 0;
check("week plan → shopping list", items > 0, `${lists.length} list(s), ${items} items`);
check("success hint links to the list", await page.getByRole("link", { name: /Zur Einkaufsliste/ }).count() > 0);

// 3. Freezer: withdraw one portion.
await page.goto(`${BASE}/household/freezer`);
await settle();
const stock = async () => Object.values((await api("/api/households/planning")).state.batches).reduce((s, b) => s + b.remaining, 0);
const s0 = await stock();
await page.getByRole("button", { name: "Entnehmen" }).first().click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: /Bestätigen/ }).click();
await settle();
check("withdraw from freezer", (await stock()) === s0 - 1, `${s0} → ${await stock()}`);

// 4. Goals: record today's weight.
await page.goto(`${BASE}/household/goals`);
await settle();
await page.getByLabel("Heute gewogen").click();
await page.getByLabel("Heute gewogen").pressSequentially("87.6", { delay: 40 });
await page.locator(".calc-weight__entry").getByRole("button", { name: "Speichern" }).click();
await settle();
const obs = Object.values((await api("/api/households/planning/me")).state.observations).sort((a, b) => a.at.localeCompare(b.at)).at(-1);
check("save manual weight", Math.abs(obs.value - 87.6) < 0.01, `${obs.value} kg`);
check("goal unchanged by redesign", (await api("/api/households/planning/me")).state.active?.goals.calories > 0);

// 5. Ideas: propose and like.
await page.goto(`${BASE}/household/ideas`);
await settle();
await page.getByRole("button", { name: /Idee vorschlagen/ }).first().click();
await page.waitForTimeout(800);
await page.locator(".pi-pick").filter({ hasText: "Linsen" }).click();
await settle();
const ideas = Object.values((await api("/api/households/planning")).state.ideas);
const idea = ideas.find(i => i.name === "Linsen-Bolognese");
check("propose idea", !!idea && idea.likes.length === 1);
await page.locator(".pi-card").filter({ hasText: "Linsen" }).locator(".pi-like").click();
await settle();
const liked = Object.values((await api("/api/households/planning")).state.ideas).find(i => i.id === idea?.id);
check("toggle like", liked?.likes.length === 0);
await page.locator(".pi-card").filter({ hasText: "Linsen" }).locator(".pi-card__remove").click();
await settle();

check("no uncaught page errors", errors.length === 0, errors.join(" | "));
await browser.close();
console.log(results.every(Boolean) ? "\nall flows passed" : "\nFAILURES");
process.exit(results.every(Boolean) ? 0 : 1);
