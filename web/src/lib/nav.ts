export const SITE_NAV = [
  { href: "/", label: "Home" },
  { href: "/screener", label: "Screener" },
  { href: "/momentum", label: "Momentum" },
  { href: "/sectors", label: "Sectors" },
  { href: "/volume-gainer", label: "Volume" },
  { href: "/analysis", label: "Strategies" },
  { href: "/ai", label: "AI Search" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/news", label: "Learn" },
] as const;

export function isNavActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
