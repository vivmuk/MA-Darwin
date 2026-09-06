import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MA·Darwin",
  description: "One PDF → one M2M deck. Revise the skill, keep what works.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
