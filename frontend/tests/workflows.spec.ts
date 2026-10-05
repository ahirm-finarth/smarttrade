import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import type { CaseDetail, CaseList, DashboardSummary } from "../types/cases";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const captureDir = path.resolve(__dirname, "../../.impeccable/review");

test("dashboard matches MySQL API, filters, empty state, and case navigation", async ({
  page,
  request,
}, info) => {
  const api = await request.get(`${apiBase}/api/v1/cases`);
  expect(api.ok()).toBeTruthy();
  const list = (await api.json()) as CaseList;
  const summary = (await (
    await request.get(`${apiBase}/api/v1/dashboard/summary`)
  ).json()) as DashboardSummary;
  expect(list.items.length).toBeGreaterThan(0);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Trade dashboard" }),
  ).toBeVisible();
  await expect(
    page.getByText("Synthetic Demo Data", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Total cases", { exact: true }).locator("..").locator("dd"),
  ).toHaveText(String(summary.total_cases));
  for (const key of ["PASS", "REFER", "BLOCK"]) {
    await expect(
      page
        .getByText(`Expected ${key}`, { exact: true })
        .locator("..")
        .locator("dd"),
    ).toHaveText(String(summary.expected_outcomes[key]));
  }
  for (const row of list.items)
    await expect(
      page.getByRole("link", { name: row.case_id, exact: true }),
    ).toBeVisible();
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
          document.documentElement.clientWidth &&
        window.innerWidth === document.documentElement.clientWidth,
    ),
  ).toBeTruthy();
  await mkdir(captureDir, { recursive: true });
  await page.screenshot({
    path: path.join(captureDir, `${info.project.name}-dashboard.png`),
    fullPage: true,
  });
  await page
    .getByRole("textbox", { name: "Search case ID or party" })
    .fill(list.items[0].case_id);
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.locator(".case-table tbody tr")).toHaveCount(1);
  await page
    .getByRole("link", { name: list.items[0].case_id, exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: list.items[0].case_id, exact: true }),
  ).toBeVisible();
  await page.goto("/?q=unmatched-case-query-for-browser-check");
  await expect(
    page.getByRole("heading", { name: "No cases match these filters" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Clear", exact: true }).click();
  await expect(page.locator(".case-table tbody tr")).toHaveCount(
    list.items.length,
  );
});

test("case workspace exposes source records, keyboard tabs, and unknown-case state", async ({
  page,
  request,
}, info) => {
  const list = (await (
    await request.get(`${apiBase}/api/v1/cases`)
  ).json()) as CaseList;
  let detail: CaseDetail | undefined;
  for (const item of list.items) {
    const candidate = (await (
      await request.get(`${apiBase}/api/v1/cases/${item.case_id}`)
    ).json()) as CaseDetail;
    if (candidate.discrepancies.length && candidate.risk_events.length) {
      detail = candidate;
      break;
    }
  }
  expect(detail).toBeDefined();
  const data = detail!;
  await page.goto(`/cases/${data.case_id}`);
  await expect(
    page.getByRole("heading", { name: data.case_id, exact: true }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("tabpanel", { name: "Overview" })
      .getByText(data.applicant!, { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
          document.documentElement.clientWidth &&
        window.innerWidth === document.documentElement.clientWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: path.join(captureDir, `${info.project.name}-case.png`),
    fullPage: true,
  });
  for (const [tab, title, count] of [
    ["Parties", "Parties", data.parties.length],
    ["Documents", "Document inventory", data.documents.length],
    ["Trade lines", "Trade lines", data.trade_lines.length],
    ["Discrepancies", "Discrepancies", data.discrepancies.length],
    ["Risk events", "Risk events", data.risk_events.length],
    ["Approvals", "Approval history", data.approvals.length],
  ] as const) {
    await page.getByRole("tab", { name: new RegExp(`^${tab}`) }).click();
    const panel = page.getByRole("tabpanel");
    await expect(
      panel.getByRole("heading", { name: new RegExp(`^${title}`) }),
    ).toBeVisible();
    if (count) await expect(panel.locator("tbody tr")).toHaveCount(count);
  }
  await page.getByRole("tab", { name: "Overview", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: /^Parties/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.keyboard.press("Home");
  await expect(
    page.getByRole("tab", { name: "Overview", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.goto("/cases/unknown-case-for-browser-check");
  await expect(
    page.getByRole("heading", { name: "Trade case not found" }),
  ).toBeVisible();
});
