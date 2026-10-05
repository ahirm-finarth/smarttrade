import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return <div className="state-page"><FileQuestion size={32} /><h1>Trade case not found</h1><p>This case ID has no record in Smart Trade. Return to the register to choose an available case.</p><Link href="/" className="button">Open case register</Link></div>;
}
