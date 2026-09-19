"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { LineChart, Menu, X } from "lucide-react";

import { MarketingSearch } from "@/components/marketing/MarketingSearch";
import { ContrastControl } from "@/components/theme/ContrastControl";
import { isNavActive, SITE_NAV } from "@/lib/nav";
import { cn } from "@/lib/utils";

export function SiteHeader() {
  const pathname = usePathname() || "/";
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-[var(--surface)]/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 lg:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2" onClick={() => setOpen(false)}>
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-[var(--accent)] text-[var(--accent-ink)]">
            <LineChart className="h-4 w-4" strokeWidth={2.4} />
          </span>
          <span className="text-base font-bold text-[var(--ink)]">NiveshGuide</span>
        </Link>

        <nav className="hidden flex-1 items-center justify-center gap-1 lg:flex">
          {SITE_NAV.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-sm font-medium transition hover:bg-[var(--hover)] hover:text-[var(--ink)]",
                isNavActive(pathname, link.href)
                  ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "text-[var(--ink-soft)]",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <MarketingSearch
            size="nav"
            className="hidden w-52 md:block xl:w-64"
            placeholder="Search stocks (e.g. TCS)"
          />
          <ContrastControl />
          <Link
            href="/watchlist"
            className="hidden rounded-md bg-[var(--accent)] px-3.5 py-2 text-sm font-semibold text-[var(--accent-ink)] transition hover:bg-[var(--accent-hover)] sm:inline-flex"
          >
            Login
          </Link>
          <button
            type="button"
            className="rounded-lg p-2 text-[var(--ink)] hover:bg-[var(--hover)] lg:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open ? (
        <div className="border-t border-[var(--line)] bg-[var(--surface)] px-4 py-3 lg:hidden">
          <nav className="grid gap-1">
            {SITE_NAV.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "rounded-md px-3 py-2 text-sm font-medium",
                  isNavActive(pathname, link.href)
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "text-[var(--ink-soft)]",
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="mt-3 md:hidden">
            <MarketingSearch size="nav" placeholder="Search stocks (e.g. TCS)" />
          </div>
        </div>
      ) : null}
    </header>
  );
}
