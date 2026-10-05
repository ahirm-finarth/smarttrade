export default function Loading() {
  return (
    <div
      className="page-content"
      role="status"
      aria-label="Loading trade case data"
    >
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-subtitle" />
      <div className="skeleton skeleton-metrics" />
      <div className="skeleton skeleton-table" />
      <span className="sr-only">Loading trade case data…</span>
    </div>
  );
}
