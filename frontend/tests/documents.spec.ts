import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import type { CaseDetail, CaseList } from "../types/cases";
import type { DocumentDetail } from "../types/documents";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const captureDir = path.resolve(__dirname, "../../.impeccable/review");

// Source-only smoke coverage against the native API; no default live LLM calls.
test("document intake, duplicate upload, source page, and fact provenance", async ({
  page,
  request,
}, info) => {
  const cases = (await (
    await request.get(`${apiBase}/api/v1/cases`)
  ).json()) as CaseList;
  let data: DocumentDetail | undefined;
  for (const item of cases.items) {
    const detail = (await (
      await request.get(`${apiBase}/api/v1/cases/${item.case_id}`)
    ).json()) as CaseDetail;
    for (const document of detail.documents) {
      if (document.processing_status !== "COMPLETED") continue;
      const candidate = (await (
        await request.get(`${apiBase}/api/v1/documents/${document.id}`)
      ).json()) as DocumentDetail;
      if (
        candidate.facts.some((fact) => fact.evidence_status === "SUPPORTED")
      ) {
        data ??= candidate;
        if (candidate.document.detected_type === "COMMERCIAL_INVOICE") {
          data = candidate;
          break;
        }
      }
    }
    if (data?.document.detected_type === "COMMERCIAL_INVOICE") break;
  }
  expect(
    data,
    "Register and explicitly process at least one demo PDF before browser tests",
  ).toBeDefined();
  const detail = data!;
  await page.goto(`/cases/${detail.case_id}?tab=documents`);
  await expect(
    page.getByRole("heading", { name: /^Document inventory/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Upload Document", exact: true }),
  ).toBeVisible();
  await page
    .locator('input[name="file"]')
    .first()
    .setInputFiles(
      path.resolve(
        __dirname,
        `../../data/demo/case_packets/${detail.case_id}/${detail.selected_version!.original_filename}`,
      ),
    );
  await page
    .getByRole("button", { name: "Upload Document", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("already registered");
  await expect(
    page.getByRole("button", { name: "Upload Document", exact: true }),
  ).toBeEnabled();
  await page.evaluate(() => window.scrollTo(0, 0));
  await mkdir(captureDir, { recursive: true });
  await page.screenshot({
    path: path.join(captureDir, `${info.project.name}-documents.png`),
    fullPage: true,
  });
  await page.goto(`/documents/${detail.document.id}`);
  await expect(
    page.getByRole("heading", {
      name: detail.selected_version!.original_filename,
      exact: true,
    }),
  ).toBeVisible();
  const image = page.getByRole("img", { name: /source page 1$/ });
  await expect(image).toBeVisible();
  await expect
    .poll(() =>
      image.evaluate((element) => (element as HTMLImageElement).naturalWidth),
    )
    .toBeGreaterThan(0);
  const source = await request.get(
    `${apiBase}/api/v1/documents/${detail.document.id}/source`,
  );
  expect(source.headers()["content-type"]).toContain("application/pdf");
  expect((await source.body()).subarray(0, 5).toString()).toBe("%PDF-");
  const fact =
    detail.facts.find(
      (item) =>
        item.field_name === "total_amount" &&
        item.evidence_status === "SUPPORTED",
    ) || detail.facts.find((item) => item.evidence_status === "SUPPORTED")!;
  const label = fact.field_name.toLowerCase().replaceAll("_", " ");
  await page
    .getByRole("button", { name: new RegExp(`^${label}`, "i") })
    .click();
  const evidence = page.getByRole("region", {
    name: "Selected field provenance",
  });
  await expect(
    evidence
      .getByText("Raw source value", { exact: true })
      .locator("..")
      .locator("dd"),
  ).toHaveText(fact.raw_value);
  await expect(evidence.locator("blockquote")).toHaveText(fact.source_text);
  await expect(evidence).toContainText(
    `Version ${detail.selected_version!.version_number} · Page ${fact.page_number} · Run ${detail.selected_run!.run_number}`,
  );
  await expect(page.getByRole("combobox", { name: "Source page" })).toHaveValue(
    String(fact.page_number),
  );
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
          document.documentElement.clientWidth &&
        window.innerWidth === document.documentElement.clientWidth,
    ),
  ).toBeTruthy();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(captureDir, `${info.project.name}-document-workspace.png`),
    fullPage: true,
  });
  // Verify failure recovery controls without triggering a billable LLM request.
  await page.route("**/api/v1/documents/*/reprocess*", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: '{"detail":"Unavailable"}',
    }),
  );
  await page.getByRole("button", { name: "Reprocess", exact: true }).click();
  await expect(page.locator(".document-notice[role=alert]")).toContainText(
    "temporarily unavailable",
  );
  await expect(
    page.getByRole("button", { name: "Reprocess", exact: true }),
  ).toBeEnabled();
  await page.goto("/documents/999999999");
  await expect(
    page.getByRole("heading", { name: "Source document not found" }),
  ).toBeVisible();
});
