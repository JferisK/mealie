// Layout regression check for the fork UI (Playwright, WebKit = iOS Safari engine).
//
// Needs a running dev stack (backend :9000, `pnpm dev` :3000) seeded with
// dev/qa/seed.py. Usage:
//   node dev/qa/layout-check.mjs [baseUrl]
// Exits non-zero when a check fails.
import { webkit } from "playwright";

const BASE = process.argv[2] || "http://localhost:3000";
const USER = process.env.QA_USER || "changeme@example.com";
const PASS = process.env.QA_PASSWORD || "MyPassword";
const WIDTHS = [320, 375, 390, 430, 768, 1280];
const ROUTES = [
  "/g/home",
  "/g/home/r/thunfisch-kichererbsen-salat",
  "/g/home/r/hahnchen-gemuse-curry-mit-basmati-und-extra-viel-frischem-koriander",
  "/household/ideas",
  "/household/portions",
  "/household/cooking",
  "/household/freezer",
  "/household/goals",
  "/shopping-lists",
  "/g/home/recipes/finder",
  "/g/home/recipes/timeline",
  "/g/home/cookbooks",
  "/user/profile",
  "/household/mealplan/planner/view",
];
// iPhone 15 insets, injected through the fork's safe-area tokens.
const SAFE = ":root{--fork-safe-top:0px!important;--fork-safe-bottom:34px!important}";

const failures = [];
const fail = (msg) => { failures.push(msg); console.log(`  ✗ ${msg}`); };

async function settle(page) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(700);
}

const browser = await webkit.launch();
let storageState;
for (const width of WIDTHS) {
  const height = width >= 1000 ? 900 : width >= 700 ? 1024 : width <= 320 ? 568 : 844;
  const ctx = await browser.newContext({ viewport: { width, height }, hasTouch: width < 700, locale: "de-DE", storageState });
  await ctx.addCookies([{ name: "i18n_redirected", value: "de-DE", url: BASE }]);
  const page = await ctx.newPage();
  if (!storageState) {
    await page.goto(`${BASE}/login`);
    await page.locator("input[type=text], input[type=email]").first().fill(USER);
    await page.locator("input[type=password]").fill(PASS);
    await page.locator("button[type=submit]").click();
    await page.waitForURL(u => !u.pathname.startsWith("/login"), { timeout: 20000 });
    storageState = await ctx.storageState();
  }
  console.log(`@${width}px`);

  for (const route of ROUTES) {
    await page.goto(BASE + route);
    await settle(page);
    // 1. No horizontal page scroll.
    const overflow = await page.evaluate(() => document.scrollingElement.scrollWidth - window.innerWidth);
    if (overflow > 0) fail(`${route}@${width}: horizontal overflow ${overflow}px`);
    // 2. Page titles keep the gutter (no full-bleed headings).
    const left = await page.evaluate(() => {
      const h = document.querySelector("main h1");
      return h ? h.getBoundingClientRect().left - document.querySelector("main").getBoundingClientRect().left : null;
    });
    if (left !== null && left < 12) fail(`${route}@${width}: page title touches the edge (${Math.round(left)}px)`);
  }

  if (width < 700) {
    // 3. Planning dialog: footer above the home indicator, long title wraps, chips are touchable.
    await page.goto(`${BASE}/household/portions`);
    await settle(page);
    await page.addStyleTag({ content: SAFE });
    await page.locator(".pw-dish").filter({ hasText: "Curry" }).first().click();
    await page.waitForTimeout(600);
    const dlg = await page.evaluate(() => {
      const actions = document.querySelector(".planner-sheet__actions");
      const title = document.querySelector(".planner-sheet__title");
      const chips = [...document.querySelectorAll(".pw-chip")].map(c => c.getBoundingClientRect().height);
      const r = actions?.getBoundingClientRect();
      return {
        footerBottom: r?.bottom,
        vh: window.innerHeight,
        titleClipped: title ? title.scrollWidth > title.clientWidth + 1 : true,
        titleRight: title?.getBoundingClientRect().right,
        minChip: Math.min(...chips),
      };
    });
    if (dlg.footerBottom === undefined) fail(`plan dialog@${width}: no footer`);
    else if (dlg.footerBottom > dlg.vh - 34 + 1) fail(`plan dialog@${width}: footer under home indicator (${dlg.footerBottom} > ${dlg.vh - 34})`);
    if (dlg.titleClipped || dlg.titleRight > width) fail(`plan dialog@${width}: title clipped`);
    if (dlg.minChip < 40) fail(`plan dialog@${width}: person chip ${dlg.minChip}px < 40px`);
    await page.keyboard.press("Escape");

    // 4. Bottom-sheet dialog on the freezer page.
    await page.goto(`${BASE}/household/freezer`);
    await settle(page);
    await page.addStyleTag({ content: SAFE });
    await page.getByRole("button", { name: "Entnehmen" }).first().click();
    await page.waitForTimeout(600);
    const sheet = await page.evaluate(() => {
      const card = document.querySelector(".planner-sheet--bottom .planner-sheet__card");
      const actions = card?.querySelector(".planner-sheet__actions");
      return { cardBottom: card?.getBoundingClientRect().bottom, actionsBottom: actions?.getBoundingClientRect().bottom, vh: window.innerHeight };
    });
    if (sheet.actionsBottom === undefined) fail(`withdraw sheet@${width}: not a bottom sheet`);
    else if (sheet.actionsBottom > sheet.vh - 34 + 1) fail(`withdraw sheet@${width}: actions under home indicator`);
  }
  await ctx.close();
}
await browser.close();
console.log(failures.length ? `\n${failures.length} failure(s)` : "\nall layout checks passed");
process.exit(failures.length ? 1 : 0);
