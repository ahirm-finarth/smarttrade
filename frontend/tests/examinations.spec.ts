import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import type { ExaminationDetail, ExaminationRun } from "../types/examinations";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const caseId = "ST-IMP-2026-0002";
const route = `/api/v1/cases/${caseId}/examinations`;
const captureDir = path.resolve(__dirname, "../../.impeccable/review");

test("examination reruns persist, history stays immutable, and both sources open", async ({
  page,
  request,
}, info) => {
  const previous = (await (
    await request.get(`${apiBase}${route}`)
  ).json()) as ExaminationRun[];
  await page.goto(`/cases/${caseId}?tab=examination`);
  await expect(
    page.getByRole("heading", { name: "Documentary examination" }),
  ).toBeVisible();
  const post = page.waitForResponse(
    (r) => r.url().endsWith(route) && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Rerun examination", exact: true })
    .click();
  const response = await post;
  expect(response.ok()).toBeTruthy();
  const result = (await response.json()) as ExaminationDetail;
  expect(result.run.id).not.toBe(previous[0]?.id);
  expect(result.run.status).toBe("DISCREPANCIES_FOUND");
  const finding = result.findings[0];
  await expect(
    page.getByRole("heading", { name: /^Calculated findings/ }),
  ).toBeVisible();
  await expect(page.getByLabel("Examination run")).toHaveValue(
    String(result.run.id),
  );
  await mkdir(captureDir, { recursive: true });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(captureDir, `${info.project.name}-examination.png`),
    fullPage: true,
  });
  await page
    .getByRole("link", {
      name: `View evidence for ${finding.title}`,
      exact: true,
    })
    .click();
  const evidence = page.getByRole("region", { name: "Comparison evidence" });
  await expect(evidence).toContainText(
    `${finding.rule_id} v${finding.rule_version}`,
  );
  for (const [title, fact] of [
    ["Expected / governing source", finding.expected_json],
    ["Observed source", finding.observed_json],
  ] as const) {
    const side = page.getByRole("region", { name: title, exact: true });
    await expect(side).toContainText(fact.raw_value);
    await expect(side.locator("blockquote")).toHaveText(fact.source_text);
    await expect(side.getByRole("link")).toHaveAttribute(
      "href",
      new RegExp(
        `version_id=${fact.document_version_id}&run_id=${fact.processing_run_id}&fact_id=${fact.fact_id}`,
      ),
    );
  }
  await page
    .getByText(`Evidence relations · ${result.relations.length}`, {
      exact: true,
    })
    .click();
  await expect(
    page
      .locator("details")
      .filter({ hasText: "Evidence relations" })
      .locator("tbody tr"),
  ).toHaveCount(result.relations.length);
  await page.getByText(/^Current extracted facts ·/).click();
  await expect(
    page
      .locator("details")
      .filter({ hasText: "Current extracted facts" })
      .locator("tbody tr"),
  ).not.toHaveCount(0);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBeTruthy();
  await page
    .getByRole("region", { name: "Observed source", exact: true })
    .getByRole("link")
    .click();
  await expect(
    page.getByRole("region", { name: "Selected field provenance" }),
  ).toContainText(finding.observed_json.raw_value);
  await expect(page.locator("#source-page img")).toBeVisible();
  await page.goto(`/cases/${caseId}?tab=examination`);
  await expect(page.getByLabel("Examination run")).toHaveValue(
    String(result.run.id),
  );
  if (previous[0]) {
    await page
      .getByLabel("Examination run")
      .selectOption(String(previous[0].id));
    await expect(page.getByLabel("Examination run")).toHaveValue(
      String(previous[0].id),
    );
    const historical = (await (
      await request.get(`${apiBase}/api/v1/examinations/${previous[0].id}`)
    ).json()) as ExaminationDetail;
    expect(historical.run.summary_json).toEqual(previous[0].summary_json);
  }
});

test("incomplete guarantee examination exposes classification review without inventing findings", async ({
  page,
  request,
}) => {
  const bg = "ST-BG-2026-0005";
  const result = (await (
    await request.get(`${apiBase}/api/v1/cases/${bg}/examinations/latest`)
  ).json()) as ExaminationDetail;
  expect(result.run.status).toBe("INCOMPLETE_EXAMINATION");
  await page.goto(`/cases/${bg}?tab=examination`);
  await expect(
    page.getByText("Incomplete examination", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "No supported discrepancies were detected. Review incomplete results before drawing a conclusion.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Observed source", exact: true }),
  ).toContainText("classification is below");
  await page.getByLabel("Result filter").selectOption("NEEDS_REVIEW");
  await expect(
    page.getByRole("heading", { name: /^Rule results/ }),
  ).toBeVisible();
});

test("failed requests recover and changed inputs warn on stored examination", async ({
  page,
  request,
}) => {
  const saved = (await (
    await request.get(`${apiBase}${route}/latest`)
  ).json()) as ExaminationDetail;
  await page.route(`**/api/v1/examinations/${saved.run.id}`, (r) =>
    r.fulfill({ json: { ...saved, inputs_current: false } }),
  );
  await page.route(`**${route}`, (r) =>
    r.request().method() === "POST"
      ? r.fulfill({ status: 503, json: { detail: "unavailable" } })
      : r.continue(),
  );
  await page.goto(`/cases/${caseId}?tab=examination`);
  await expect(
    page.getByText(/^Source facts, rules or confidence settings have changed/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Rerun examination", exact: true })
    .click();
  await expect(
    page.getByRole("tabpanel", { name: "Examination" }).getByRole("alert"),
  ).toContainText("temporarily unavailable");
  await page
    .getByRole("button", { name: "Refresh history", exact: true })
    .click();
  await expect(
    page.getByRole("tabpanel", { name: "Examination" }).getByRole("alert"),
  ).toHaveCount(0);
});
