"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="page-content state-page">
      <h1>Document could not load</h1>
      <p>
        Check that the backend is running, then try loading the document again.
      </p>
      <button className="button button-primary" onClick={reset}>
        Try again
      </button>
    </div>
  );
}
