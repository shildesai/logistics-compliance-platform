import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Logistics Compliance Intelligence Platform",
  description:
    "Continuous assurance and audit readiness for logistics operators and outsourced transport supply chains.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
