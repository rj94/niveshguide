import type { Metadata } from "next";
import { Geist_Mono, Plus_Jakarta_Sans } from "next/font/google";

import { AdSenseScript } from "@/components/ads/AdSenseScript";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import "./globals.css";

const body = Plus_Jakarta_Sans({
  variable: "--font-body",
  subsets: ["latin"],
});

// Keep legacy --font-display references working on stock/screener pages.
const display = Plus_Jakarta_Sans({
  variable: "--font-display",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "NiveshGuide — Market Platform",
  description:
    "NiveshGuide — dashboard, sectors, screener, momentum, and stock research for Indian markets.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${body.variable} ${display.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full font-[family-name:var(--font-body)]">
        <AdSenseScript />
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
