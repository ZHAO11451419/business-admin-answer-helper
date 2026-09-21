import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BAH — Business Academic Helper",
  description: "A business-study copilot for explanations, calculations, case analysis, and report structure.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
