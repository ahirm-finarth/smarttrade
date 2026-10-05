import Link from "next/link";
import { ArrowUpRight, BookOpen, Layers3 } from "lucide-react";

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <aside className="sidebar" aria-label="Application navigation">
        <Link href="/" className="wordmark" aria-label="FinArth Smart Trade home">FinArth<span>Smart Trade</span></Link>
        <div className="sidebar-rule" />
        <nav>
          <Link className="nav-link" href="/"><Layers3 size={18} /> Dashboard</Link>
          <Link className="nav-link" href="/#case-register"><BookOpen size={18} /> Case register<ArrowUpRight size={14} className="nav-end" /></Link>
        </nav>
        <div className="sidebar-note"><span className="phase-label">PHASE 1</span><p>A foundation for governed trade operations.</p><span className="read-only">Read-only workspace</span></div>
        <div className="sidebar-foot">FinArth Smart Trade<span>Synthetic demonstration</span></div>
      </aside>
      <div className="main-shell">
        <header className="topbar"><span>Trade operations</span><span className="demo-indicator"><span className="demo-dot" />Synthetic Demo Data</span></header>
        <main id="main" tabIndex={-1}>{children}</main>
        <footer className="app-footer"><span>FinArth Smart Trade · Phase 1</span><span>Expected outcomes are supplied demo references.</span></footer>
      </div>
    </div>
  );
}
