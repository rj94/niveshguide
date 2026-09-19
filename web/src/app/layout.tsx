import type { Metadata } from "next";
import { Geist_Mono, Plus_Jakarta_Sans } from "next/font/google";

import { AdSenseScript } from "@/components/ads/AdSenseScript";
import { ThemeScript } from "@/components/theme/ThemeScript";
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
  title: "NiveshGuide - Market Platform",
  description:
    "NiveshGuide - dashboard, sectors, screener, momentum, and stock research for Indian markets.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${jakarta.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[var(--background)] font-[family-name:var(--font-body)] text-[var(--foreground)]">
        <ThemeScript />
        <AdSenseScript />
        {children}
      </body>
    </html>
  );
}
