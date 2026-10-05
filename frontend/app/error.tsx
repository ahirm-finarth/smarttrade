"use client";
import Link from "next/link";
import { CircleAlert } from "lucide-react";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="state-page">
      <CircleAlert size={32} />
      <h1>Case data is unavailable</h1>
      <p>
        Smart Trade couldn’t load its records. Check that the API and database
        are running, then retry.
      </p>
      <div className="button-row">
        <button className="button" onClick={reset}>
          Try again
        </button>
        <Link href="/" className="button button-secondary">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
