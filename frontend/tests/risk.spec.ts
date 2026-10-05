import { test, expect } from "@playwright/test";
import path from "node:path";
import { mkdir } from "node:fs/promises";
import type { RiskDetail, RiskRun } from "../types/risk";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const caseId = "ST-IMP-2026-0002";
const endpoint = `/api/v1/cases/${caseId}/risk-runs`;
const captures = path.resolve(__dirname, "../../.impeccable/review");

test("risk rerun persists findings, exact source evidence, provider policy and history", async ({
  page,
  request,
}, info) => {
  const old = (await (
    await request.get(apiBase + endpoint)
  ).json()) as RiskRun[];
  await page.goto(`/cases/${caseId}?tab=risk_compliance`);
  await expect(
    page.getByRole("heading", { name: "Risk & Compliance", exact: true }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page
        .getByRole("tab", {
          name: "Risk & Compliance",
          exact: true,
        })
        .evaluate((tab) => {
          const strip = tab.parentElement!.getBoundingClientRect();
          const selected = tab.getBoundingClientRect();
          return (
            selected.left >= strip.left - 1 && selected.right <= strip.right + 1
          );
        }),
    )
    .toBeTruthy();
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  const post = page.waitForResponse(
    (r) => r.url().endsWith(endpoint) && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Rerun risk checks", exact: true })
    .click();
  const response = await post;
  expect(response.ok()).toBeTruthy();
  const next = (await response.json()) as RiskDetail;
  expect(next.run.id).not.toBe(old[0].id);
  expect(next.findings).toHaveLength(3);
  await expect(page.getByLabel("Risk run")).toHaveValue(String(next.run.id));
  const panel = page.getByRole("tabpanel", {
    name: "Risk & Compliance",
    exact: true,
  });
  await expect(panel).not.toContainText(/\bPASS\b|\bREFER\b|\bBLOCK\b/);
  const vessel = next.findings.find((f) => f.category === "vessel")!;
  await page
    .getByRole("link", {
      name: `View risk evidence for ${vessel.title}`,
      exact: true,
    })
    .click();
  const source = page.getByRole("region", {
    name: "Originating source",
    exact: true,
  });
  const evidence = vessel.evidence_json.subject.evidence[0];
  await expect(source).toContainText(evidence.raw_value);
  await expect(source.locator("blockquote").first()).toHaveText(
    evidence.source_text,
  );
  await expect(
    page.getByRole("region", { name: "Provider and policy", exact: true }),
  ).toContainText("DEMO-SCR-002");
  await expect(
    page.getByRole("region", { name: "Provider and policy", exact: true }),
  ).toContainText(`${vessel.rule_id} v${vessel.rule_version}`);
  await mkdir(captures, { recursive: true });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(captures, `${info.project.name}-risk.png`),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBeTruthy();
  await source
    .getByRole("link", { name: /Open original source/ })
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Selected field provenance" }),
  ).toContainText(evidence.raw_value);
  await page.goto(`/cases/${caseId}?tab=risk_compliance`);
  await expect(page.getByLabel("Risk run")).toHaveValue(String(next.run.id));
  await page.getByLabel("Risk run").selectOption(String(old[0].id));
  await expect(page.getByLabel("Risk run")).toHaveValue(String(old[0].id));
  const stored = (await (
    await request.get(`${apiBase}/api/v1/risk-runs/${old[0].id}`)
  ).json()) as RiskDetail;
  expect(stored.run.summary_json).toEqual(old[0].summary_json);
  const duplicates = await request.get(
    `${apiBase}/api/v1/cases/${caseId}/duplicate-candidates`,
  );
  expect(duplicates.ok()).toBeTruthy();
  expect((await duplicates.json()).financing_status).toBe("NOT_CHECKED");
});

test("clean risk run shows missing reference checks without clearance claim", async ({
  page,
}) => {
  await page.goto("/cases/ST-IMP-2026-0001?tab=risk_compliance");
  await expect(
    page.getByText(
      "No risk findings were generated. Review unchecked and incomplete checks; this is not a clearance decision.",
    ),
  ).toBeVisible();
  await page.getByLabel("Risk category").selectOption("fair_value");
  await expect(
    page
      .getByRole("cell", {
        name: "No matching synthetic price band; no reference market price invented",
        exact: true,
      })
      .filter({ visible: true }),
  ).toBeVisible();
});

test("risk failure recovery, stale inputs and partial provider errors remain visible", async ({
  page,
  request,
}) => {
  const saved = (await (
    await request.get(apiBase + endpoint + "/latest")
  ).json()) as RiskDetail;
  const partial = {
    ...saved,
    inputs_current: false,
    run: { ...saved.run, status: "PARTIAL" },
    checks: saved.checks.map((c, i) =>
      i === 0
        ? {
            ...c,
            status: "PROVIDER_ERROR",
            result_json: {
              ...c.result_json,
              status: "PROVIDER_ERROR",
              reason: "Provider failed; private diagnostics suppressed",
            },
          }
        : c,
    ),
  };
  await page.route(`**/api/v1/risk-runs/${saved.run.id}`, (r) =>
    r.fulfill({ json: partial }),
  );
  await page.route(`**${endpoint}`, (r) =>
    r.request().method() === "POST"
      ? r.fulfill({ status: 503, json: { detail: "unavailable" } })
      : r.continue(),
  );
  await page.goto(`/cases/${caseId}?tab=risk_compliance`);
  await expect(page.getByText("Partial", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/^Current inputs, provider references or policies changed/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Rerun risk checks", exact: true })
    .click();
  const panel = page.getByRole("tabpanel", {
    name: "Risk & Compliance",
    exact: true,
  });
  await expect(panel.getByRole("alert")).toContainText(
    "temporarily unavailable",
  );
  await page
    .getByRole("button", { name: "Refresh risk history", exact: true })
    .click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
});
