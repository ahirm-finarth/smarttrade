import Link from "next/link";
export default function NotFound() {
  return (
    <div className="page-content state-page">
      <h1>Source document not found</h1>
      <p>Return to the case register and select an available document.</p>
      <Link className="button button-primary" href="/">
        Case register
      </Link>
    </div>
  );
}
