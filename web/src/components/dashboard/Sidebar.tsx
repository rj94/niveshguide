"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  LayoutDashboard,
  LineChart,
  Search,
  Sparkles,
  TrendingUp,
  X,
} from "lucide-react";

import { cn } from "@/lib/utils";

const PRIMARY_NAV = [
  { href: "/desk", label: "Desk", icon: LayoutDashboard },
  { href: "/screener", label: "Screeners", icon: Search },
  { href: "/momentum", label: "Momentum", icon: TrendingUp },
  { href: "/volume-gainer", label: "Volume", icon: Activity },
  { href: "/analysis", label: "Strategies", icon: Sparkles },
] as const;

type Props = {
  open: boolean;
  onClose: () => void;
};

function isNavActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLink({
  href,
  label,
  icon: Icon,
  active,
  onClose,
}: {
  href: string;
  label: string;
  icon: (typeof PRIMARY_NAV)[number]["icon"];
  active: boolean;
  onClose: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClose}
      className={cn(
        "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] transition",
        active
          ? "bg-[var(--accent)] font-medium text-white shadow-[0_8px_20px_rgba(99,102,241,0.28)]"
          : "text-[var(--ink-soft)] hover:bg-white/[0.04] hover:text-[var(--ink)]",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" strokeWidth={active ? 2.25 : 1.75} />
      {label}
    </Link>
  );
}

export function Sidebar({ open, onClose }: Props) {
  const pathname = usePathname();

  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-40 bg-black/50 transition-opacity lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onClose}
        aria-hidden
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[var(--sidebar-w)] flex-col border-r border-[var(--line)] bg-[var(--surface)] transition-transform duration-200 lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-[var(--header-h)] items-center justify-between px-3">
          <Link href="/" className="flex items-center gap-2" onClick={onClose}>
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
              <LineChart className="h-3.5 w-3.5" strokeWidth={2.25} />
            </span>
            <span className="text-[15px] font-semibold tracking-tight text-[var(--ink)]">
              NiveshGuide
            </span>
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-[var(--ink-muted)] hover:bg-white/5 hover:text-[var(--ink)] lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="dashboard-scroll flex-1 overflow-y-auto px-2 py-1.5 pb-4">
          <ul className="space-y-0.5">
            {PRIMARY_NAV.map((item) => (
              <li key={`${item.label}-${item.href}`}>
                <NavLink
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={isNavActive(pathname, item.href)}
                  onClose={onClose}
                />
              </li>
            ))}
          </ul>
        </nav>
      </aside>
    </>
  );
}

/** Static shell used while searchParams suspense resolves — keeps Zone 1 filled. */
export function SidebarFallback({ open }: { open: boolean }) {
  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex w-[var(--sidebar-w)] flex-col border-r border-[var(--line)] bg-[var(--surface)] transition-transform duration-200 lg:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
      )}
    >
      <div className="flex h-[var(--header-h)] items-center px-3">
        <span className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
            <LineChart className="h-3.5 w-3.5" strokeWidth={2.25} />
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-[var(--ink)]">
            NiveshGuide
          </span>
        </span>
      </div>
      <nav className="flex-1 px-2 py-1.5">
        <ul className="space-y-0.5">
          {PRIMARY_NAV.map((item) => {
            const Icon = item.icon;
            return (
              <li key={`${item.label}-${item.href}`}>
                <span className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] text-[var(--ink-soft)]">
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </span>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
