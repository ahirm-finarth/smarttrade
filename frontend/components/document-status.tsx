export const activeStatuses = new Set([
  "PARSING",
  "PARSED",
  "CLASSIFYING",
  "EXTRACTING",
]);
export function readable(value: string | null) {
  if (!value) return "Not detected";
  return value
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (letter) => letter.toUpperCase());
}
export function DocumentStatus({ status }: { status: string }) {
  const tone =
    status === "COMPLETED" || status === "SUPPORTED"
      ? "supported"
      : status === "FAILED"
        ? "failed"
        : status === "NEEDS_REVIEW"
          ? "review"
          : "neutral";
  const label =
    status === "SUPPORTED"
      ? "Source matched"
      : status === "NOT_REGISTERED"
        ? "Source pending"
        : readable(status);
  return <span className={`document-status status-${tone}`}>{label}</span>;
}
