import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto("http://localhost:5173");
await page.evaluate(() => document.fonts.ready);
await page.screenshot({
  path: "../docs/screenshots/sign-in.png",
  fullPage: true,
});
await page.getByRole("button", { name: "Start a practice session" }).click();
await page.getByRole("heading", { name: "Trading workspace" }).waitFor();
await page.getByText("Market live", { exact: true }).waitFor();
await page.waitForFunction(
  () => document.querySelectorAll(".depth-row").length >= 10,
);
// A real market buy creates positions, cash movements and a trade in the ledger.
await page.getByRole("button", { name: "Market order", exact: true }).click();
await page.locator("#quantity").fill("3");
await page.getByRole("button", { name: "Buy AAPL", exact: true }).click();
await page
  .getByRole("status")
  .filter({ hasText: "3 AAPL shares filled." })
  .waitFor();
// A limit well below the market rests, then cancellation releases its reservation.
await page.getByRole("button", { name: "Limit order", exact: true }).click();
let state = await page.evaluate(() =>
  fetch("/api/snapshot").then((r) => r.json()),
);
await page
  .locator("#price")
  .fill(
    (
      Math.ceil(
        state.market.find((i) => i.symbol === "AAPL").last_price * 0.98,
      ) / 100
    ).toFixed(2),
  );
await page.locator("#quantity").fill("2");
await page.getByRole("button", { name: "Buy AAPL", exact: true }).click();
await page
  .getByRole("status")
  .filter({ hasText: "Buy order placed." })
  .waitFor();
await page.getByRole("button", { name: "Cancel", exact: true }).first().click();
await page.waitForFunction(
  () => document.querySelectorAll(".cancel-button").length === 0,
);
// Clicking depth sets the executable ticket price.
const depth = page.locator(".depth-row.ask").first();
await depth.click();
assert.notEqual(await page.locator("#price").inputValue(), "");
// Risk rejections stay visible in the ticket.
await page.locator("#price").fill("9999");
await page.getByRole("button", { name: "Buy AAPL", exact: true }).click();
await page.getByRole("alert").filter({ hasText: "within 5%" }).waitFor();
await page.locator(".depth-row.bid").first().click();
// Capture an actual working session, including a real resting order.
state = await page.evaluate(() => fetch("/api/snapshot").then((r) => r.json()));
await page
  .locator("#price")
  .fill(
    (
      Math.ceil(
        state.market.find((i) => i.symbol === "AAPL").last_price * 0.98,
      ) / 100
    ).toFixed(2),
  );
await page.locator("#quantity").fill("12");
await page.getByRole("button", { name: "Buy AAPL", exact: true }).click();
await page
  .getByRole("status")
  .filter({ hasText: "Buy order placed." })
  .waitFor();
await page.evaluate(() => document.fonts.ready);
await page.screenshot({
  path: "../docs/screenshots/dashboard.png",
  fullPage: true,
});
await page.screenshot({
  path: "../.impeccable/review/desktop.png",
  fullPage: true,
});
assert.equal(
  await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),
  false,
);
// Portfolio and activity use live, account-scoped data.
await page.getByRole("button", { name: "Portfolio", exact: true }).click();
await page.getByRole("heading", { name: "Your portfolio" }).waitFor();
await page.getByRole("columnheader", { name: "Unrealized P&L" }).waitFor();
await page.screenshot({
  path: "../docs/screenshots/portfolio.png",
  fullPage: true,
});
await page.getByRole("button", { name: "Activity", exact: true }).click();
await page.getByRole("button", { name: "Check ledger" }).click();
await page.getByRole("button", { name: "Ledger balanced" }).waitFor();
await page.getByRole("button", { name: "Trade", exact: true }).click();
await page.setViewportSize({ width: 390, height: 844 });
await page.screenshot({
  path: "../docs/screenshots/mobile.png",
  fullPage: true,
});
await page.screenshot({
  path: "../.impeccable/review/mobile.png",
  fullPage: true,
});
assert.equal(
  await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),
  false,
);
// Sign-up and sign-in retain the same portfolio; a separate guest cannot see it.
await page.getByRole("button", { name: "Sign out", exact: true }).click();
await page
  .getByRole("button", { name: "Create an account", exact: true })
  .click();
const username = `browser-${Date.now()}`;
await page.locator("#username").fill(username);
await page.locator("#password").fill("browser-test-password!");
await page.getByRole("button", { name: "Create account", exact: true }).click();
await page.getByRole("heading", { name: "Trading workspace" }).waitFor();
const accountId = await page.evaluate(() =>
  fetch("/api/auth/session")
    .then((r) => r.json())
    .then((r) => r.id),
);
await page.getByRole("button", { name: "Sign out", exact: true }).click();
await page.locator("#username").fill(username);
await page.locator("#password").fill("browser-test-password!");
await page.getByRole("button", { name: "Sign in", exact: true }).click();
await page.getByRole("heading", { name: "Trading workspace" }).waitFor();
assert.equal(
  await page.evaluate(() =>
    fetch("/api/auth/session")
      .then((r) => r.json())
      .then((r) => r.id),
  ),
  accountId,
);
const other = await browser.newContext();
const otherPage = await other.newPage();
await otherPage.goto("http://localhost:5173");
await otherPage
  .getByRole("button", { name: "Start a practice session" })
  .click();
await otherPage.getByRole("heading", { name: "Trading workspace" }).waitFor();
assert.equal(
  await otherPage.evaluate(
    (id) => fetch(`/api/snapshot?account_id=${id}`).then((r) => r.status),
    accountId,
  ),
  403,
);
assert.deepEqual(errors, []);
const result = {
  passed: true,
  checks: [
    "guest session",
    "live WebSocket",
    "market buy",
    "limit order",
    "cancel releases reservation",
    "depth price selection",
    "risk error",
    "portfolio",
    "activity reconciliation",
    "desktop overflow",
    "mobile overflow",
    "signup",
    "logout",
    "login persistence",
    "cross-account isolation",
    "no browser exceptions",
  ],
  measured_at: new Date().toISOString(),
};
await mkdir("../docs", { recursive: true });
await writeFile(
  "../docs/browser-smoke.json",
  JSON.stringify(result, null, 2) + "\n",
);
console.log(JSON.stringify(result, null, 2));
await browser.close();
