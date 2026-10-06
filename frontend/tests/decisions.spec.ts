import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";
import path from "node:path";
import { mkdir } from "node:fs/promises";
import type { DecisionDetail, AuditEntry } from "../types/decisions";

test.setTimeout(120_000);

const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const clean = "ST-IMP-2026-0001";
const risk = "ST-IMP-2026-0002";
const guarantee = "ST-BG-2026-0005";
async function generate(request: APIRequestContext, id: string) {
  const response = await request.post(`${api}/api/v1/cases/${id}/decisions`, {
    data: { request_id: crypto.randomUUID() },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as DecisionDetail;
}
async function actor(page: Page, value: string) {
  const panel = page.locator("#panel-workflow");
  const response = page.waitForResponse(
    (r) =>
      r.url().includes(`/decisions/`) && r.url().endsWith(`actor_id=${value}`),
  );
  await panel.getByLabel("Demo actor").selectOption(value);
  await response;
  await expect(panel.locator(".decision-workspace")).toHaveAttribute(
    "aria-busy",
    "false",
  );
}
async function taskAction(
  page: Page,
  kind: string,
  action: string,
  rationale: string,
) {
  const panel = page.locator("#panel-workflow");
  const section = panel
    .locator(".workflow-task")
    .filter({ has: page.getByText(new RegExp(`Task #[0-9]+ · ${kind}`, "i")) })
    .filter({
      has: page.getByRole("button", {
        name: "Record task action",
        exact: true,
      }),
    })
    .last();
  await section.locator("select").first().selectOption(action);
  await section.getByRole("textbox").fill(rationale);
  const response = page.waitForResponse(
    (r) => r.url().includes("/actions") && r.request().method() === "POST",
  );
  await section
    .getByRole("button", { name: "Record task action", exact: true })
    .click();
  const saved = await response;
  expect(saved.ok()).toBeTruthy();
  await expect(panel.locator(".decision-workspace")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  return (await saved.json()) as DecisionDetail;
}
async function capture(page: Page, project: string, name: string) {
  if (process.env.PHASE5_CAPTURE !== "1") return;
  const dir = path.resolve(__dirname, "../../.impeccable/review");
  await mkdir(dir, { recursive: true });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(dir, `phase5-${project}-${name}-viewport.png`),
  });
  await page.screenshot({
    path: path.join(dir, `phase5-${project}-${name}.png`),
    fullPage: true,
  });
}
async function noOverflow(page: Page) {
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBeTruthy();
}

test("decision reasons preserve exact source runs, original quotations and version history", async ({
  page,
  request,
}, info) => {
  const before = await generate(request, risk);
  await page.goto(`/cases/${risk}?tab=decision`);
  await expect(
    page
      .locator("[role=tabpanel]:not([hidden])")
      .getByLabel("Decision version"),
  ).toHaveValue(String(before.run.id));
  const result = page.waitForResponse(
    (r) =>
      r.url().endsWith(`/cases/${risk}/decisions`) &&
      r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Regenerate decision", exact: true })
    .click();
  const next = (await (await result).json()) as DecisionDetail;
  expect(next.run.recommended_decision).toBe("REFER");
  expect(next.effective_final_outcome).toBeNull();
  expect(next.run.id).not.toBe(before.run.id);
  await expect(
    page
      .locator("[role=tabpanel]:not([hidden])")
      .getByLabel("Decision version"),
  ).toHaveValue(String(next.run.id));
  await expect(
    page.getByText("Pending human approval", { exact: true }),
  ).toBeVisible();
  const reason = next.reasons.find((r) => r.documentary_finding_pk)!;
  await page
    .getByRole("link", {
      name: `Inspect decision reason ${reason.id}`,
      exact: true,
    })
    .click();
  const evidence = page.getByRole("region", {
    name: "Decision reason evidence",
    exact: true,
  });
  await expect(evidence.locator("blockquote").first()).not.toBeEmpty();
  const sourceHref = await evidence
    .getByRole("link", { name: "Open original source", exact: true })
    .first()
    .getAttribute("href");
  expect(sourceHref).toMatch(/version_id=\d+&run_id=\d+&fact_id=\d+/);
  await noOverflow(page);
  await capture(page, info.project.name, "decision");
  await page
    .getByRole("link", {
      name: new RegExp(`Examination #${next.run.examination_run_pk} ·`),
    })
    .click();
  await expect(page.getByLabel("Examination run")).toHaveValue(
    String(next.run.examination_run_pk),
  );
  await page.goto(`/cases/${risk}?tab=decision&decision_id=${before.run.id}`);
  await expect(
    page
      .locator("[role=tabpanel]:not([hidden])")
      .getByLabel("Decision version"),
  ).toHaveValue(String(before.run.id));
  await expect(page.getByText(/^Decision is stale/)).toBeVisible();
});

test("demo maker checker segregation, final approval and unified audit source navigation", async ({
  page,
  request,
}, info) => {
  const initial = await generate(request, clean);
  expect(initial.run.recommended_decision).toBe("PASS");
  await page.goto(`/cases/${clean}?tab=workflow`);
  await expect(
    page
      .locator("[role=tabpanel]:not([hidden])")
      .getByLabel("Decision version"),
  ).toHaveValue(String(initial.run.id));
  await actor(page, "dual.demo");
  const made = await taskAction(
    page,
    "Trade Maker",
    "SUBMIT_FOR_CHECKER",
    "Synthetic browser maker review of current evidence.",
  );
  await expect(page.getByText(/^Segregation of duties:/)).toBeVisible();
  const checker = made.tasks.find((t) => t.task_type === "CHECKER_APPROVAL")!;
  expect(
    (
      await request.post(`${api}/api/v1/tasks/${checker.id}/actions`, {
        data: {
          action: "APPROVE",
          actor_id: "dual.demo",
          comment: "Self approval attempt",
          expected_revision: made.workflow!.revision,
        },
      })
    ).status(),
  ).toBe(403);
  await actor(page, "checker.demo");
  await capture(page, info.project.name, "workflow");
  const approved = await taskAction(
    page,
    "Trade Checker",
    "APPROVE",
    "Synthetic independent browser checker review complete.",
  );
  expect(approved.effective_final_outcome).toBe("PASS");
  expect(approved.run.recommended_decision).toBe("PASS");
  await expect(
    page.getByRole("button", { name: "Record task action", exact: true }),
  ).toHaveCount(0);
  const response = await request.get(`${api}/api/v1/cases/${clean}/audit`);
  const entries = (await response.json()) as AuditEntry[];
  for (const type of [
    "DOCUMENT_PROCESSING",
    "DOCUMENTARY_EXAMINATION",
    "RISK_RUN",
    "DECISION_RUN",
    "MAKER_SUBMITTED",
    "CHECKER_APPROVED",
    "FINAL_PASS",
  ])
    expect(entries.some((r) => r.event_type === type)).toBeTruthy();
  await page.getByRole("tab", { name: "Audit", exact: true }).click();
  await page.getByLabel("Audit event type").selectOption("DECISION_RUN");
  await expect(
    page.getByRole("region", { name: "Case audit history" }),
  ).toBeVisible();
  await noOverflow(page);
  await capture(page, info.project.name, "audit");
  await page
    .getByRole("link", { name: `Open source #${approved.run.id}`, exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("tab", { name: "Decision", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    page
      .locator("[role=tabpanel]:not([hidden])")
      .getByLabel("Decision version"),
  ).toHaveValue(String(approved.run.id));
});

test("REFER specialist review and supervisor acceptance remain separate from maker checker", async ({
  page,
  request,
}) => {
  const initial = await generate(request, risk);
  await page.goto(`/cases/${risk}?tab=workflow`);
  await expect(
    page
      .locator("[role=tabpanel]:not([hidden])")
      .getByLabel("Decision version"),
  ).toHaveValue(String(initial.run.id));
  await actor(page, "compliance.demo");
  await taskAction(
    page,
    "Trade Compliance",
    "CONFIRM_CLEAR",
    "Synthetic review of demo risk candidates; no live provider clearance.",
  );
  await actor(page, "trade.demo");
  await taskAction(
    page,
    "Trade Reviewer",
    "CONFIRM_ISSUE",
    "Original documentary source mismatches confirmed for synthetic review.",
  );
  await actor(page, "supervisor.demo");
  const form = page.getByRole("region", {
    name: "Supervisor exception acceptance",
  });
  for (const checkbox of await form.getByRole("checkbox").all())
    await checkbox.check();
  await form
    .getByLabel("Exception acceptance rationale")
    .fill(
      "Synthetic reviewed exception acceptance only, without real customer waiver.",
    );
  const wait = page.waitForResponse(
    (r) => r.url().endsWith("/override") && r.request().method() === "POST",
  );
  await form
    .getByRole("button", { name: "Record exception acceptance", exact: true })
    .click();
  const overridden = (await (await wait).json()) as DecisionDetail;
  expect(overridden.run.recommended_decision).toBe("REFER");
  expect(overridden.effective_final_outcome).toBeNull();
  await expect(
    page.locator("#panel-workflow .decision-workspace"),
  ).toHaveAttribute("aria-busy", "false");
  await actor(page, "maker.demo");
  await taskAction(
    page,
    "Trade Maker",
    "SUBMIT_FOR_CHECKER",
    "Synthetic maker review after recorded specialist and supervisor reviews.",
  );
  await actor(page, "checker.demo");
  const final = await taskAction(
    page,
    "Trade Checker",
    "APPROVE",
    "Synthetic independent checker approves the governed demo outcome.",
  );
  expect(final.run.recommended_decision).toBe("REFER");
  expect(final.effective_final_outcome).toBe("PASS");
  expect(final.overrides).toHaveLength(1);
  await noOverflow(page);
});

test("incomplete guarantee stays referred; stale decisions and optional advisory errors are visible", async ({
  page,
  request,
}) => {
  const initial = await generate(request, guarantee);
  expect(initial.run.recommended_decision).toBe("REFER");
  expect(
    initial.reasons.filter((r) => r.reason_code === "INCOMPLETE_EXAMINATION"),
  ).toHaveLength(6);
  await page.goto(`/cases/${guarantee}?tab=workflow`);
  await expect(
    page
      .locator("[role=tabpanel]:not([hidden])")
      .getByLabel("Decision version"),
  ).toHaveValue(String(initial.run.id));
  await actor(page, "legal.demo");
  const pending = await taskAction(
    page,
    "Legal Reviewer",
    "REQUEST_INFORMATION",
    "Source-backed guarantee comparison review required; no breach invented.",
  );
  expect(pending.workflow!.state).toBe("NEEDS_INFORMATION");
  expect(pending.effective_final_outcome).toBeNull();
  expect(pending.resolutions).toHaveLength(0);
  await page.goto(`/cases/${guarantee}?tab=decision`);
  await page.route(
    `**/api/v1/decisions/${initial.run.id}/exception-summary`,
    (r) =>
      r.fulfill({
        status: 503,
        json: { detail: "Advisory summary unavailable" },
      }),
  );
  await page
    .getByText("Optional Exception Resolution Agent", { exact: true })
    .click();
  await page
    .getByRole("button", { name: "Draft exception summary", exact: true })
    .click();
  await expect(
    page.locator("#panel-decision").getByRole("alert"),
  ).toContainText(/unavailable/);
  await page
    .getByRole("button", { name: "Refresh decision history", exact: true })
    .click();
  await expect(page.locator("#panel-decision").getByRole("alert")).toHaveCount(
    0,
  );
  await page.route(
    `**/api/v1/decisions/${initial.run.id}?actor_id=*`,
    async (r) => {
      const saved = await (await r.fetch()).json();
      await r.fulfill({
        json: {
          ...saved,
          inputs_current: false,
          effective_final_outcome: null,
          tasks: saved.tasks.map((t: Record<string, unknown>) => ({
            ...t,
            available_actions: [],
          })),
        },
      });
    },
  );
  await page
    .getByRole("button", { name: "Refresh decision history", exact: true })
    .click();
  await expect(page.getByText(/^Decision is stale/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Draft exception summary", exact: true }),
  ).toBeDisabled();
  await noOverflow(page);
});
