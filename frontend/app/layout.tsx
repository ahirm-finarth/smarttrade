import type { Metadata } from "next";
import { Shell } from "@/components/shell";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Smart Trade · FinArth", template: "%s · Smart Trade" },
  description: "FinArth Smart Trade Phase 1 synthetic trade operations workspace",
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><Shell>{children}</Shell></body></html>;
}
