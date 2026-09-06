import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MA-Darwin — Review desk",
  description: "Generate, gate, and review MSL physician decks from a claim ledger.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
