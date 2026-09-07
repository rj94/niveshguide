import type { Metadata } from "next";
import { Geist_Mono, Plus_Jakarta_Sans } from "next/font/google";

import { AdSenseScript } from "@/components/ads/AdSenseScript";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { loadTickerItems } from "@/lib/load-dashboard";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-body",
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

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const tickerItems = await loadTickerItems().catch(() => []);

  return (
    <html
      lang="en"
      className={`${jakarta.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full font-[family-name:var(--font-body)]">
        <AdSenseScript />
        <DashboardShell tickerItems={tickerItems}>{children}</DashboardShell>
      </body>
    </html>
  );
}
