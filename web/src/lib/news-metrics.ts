import { formatNumber, formatPct } from "@/lib/format";
import type { EventAttribute, NewsEventCard, NewsMetrics, SectorProfile } from "@/types/news";

export function emptyMetrics(): NewsMetrics {
  return {
    revenue_yoy_pct: null,
    revenue_qoq_pct: null,
    ebitda_yoy_pct: null,
    pat_yoy_pct: null,
    pat_qoq_pct: null,
    eps_yoy_pct: null,
    ocf_yoy_pct: null,
    revenue_cr: null,
    ebitda_cr: null,
    pat_cr: null,
    order_value_cr: null,
    order_to_revenue_pct: null,
    materiality_band: null,
  };
}

function attrNum(attrs: EventAttribute[] | undefined, key: string): number | null {
  if (!attrs?.length) return null;
  const hit = attrs.find((a) => a.key === key);
  if (!hit || hit.value_number == null || hit.value_number === "") return null;
  const n = typeof hit.value_number === "number" ? hit.value_number : Number(hit.value_number);
  return Number.isFinite(n) ? n : null;
}

function attrText(attrs: EventAttribute[] | undefined, key: string): string | null {
  if (!attrs?.length) return null;
  const hit = attrs.find((a) => a.key === key);
  const t = hit?.value_text?.trim();
  return t || null;
}

/** Prefer API `metrics`; fall back to event_attributes so UI stays in sync after reprocess. */
export function metricsOf(item: NewsEventCard): NewsMetrics {
  const base = item.metrics ?? emptyMetrics();
  const attrs = item.attributes;
  const orderFromInr = (() => {
    const inr = attrNum(attrs, "order_value_inr");
    if (inr == null) return null;
    return Math.round((inr / 1e7) * 100) / 100;
  })();
  const orderCr =
    base.order_value_cr ??
    (attrNum(attrs, "order_value_inr") != null ? attrNum(attrs, "amount_crore") ?? orderFromInr : null);

  return {
    revenue_yoy_pct: base.revenue_yoy_pct ?? attrNum(attrs, "revenue_yoy_pct"),
    revenue_qoq_pct: base.revenue_qoq_pct ?? attrNum(attrs, "revenue_qoq_pct"),
    ebitda_yoy_pct: base.ebitda_yoy_pct ?? attrNum(attrs, "ebitda_yoy_pct"),
    pat_yoy_pct: base.pat_yoy_pct ?? attrNum(attrs, "pat_yoy_pct"),
    pat_qoq_pct: base.pat_qoq_pct ?? attrNum(attrs, "pat_qoq_pct"),
    eps_yoy_pct: base.eps_yoy_pct ?? attrNum(attrs, "eps_yoy_pct"),
    ocf_yoy_pct:
      base.ocf_yoy_pct ?? attrNum(attrs, "ocf_yoy_pct") ?? attrNum(attrs, "cfo_yoy_pct"),
    revenue_cr: base.revenue_cr ?? attrNum(attrs, "revenue_cr"),
    ebitda_cr: base.ebitda_cr ?? attrNum(attrs, "ebitda_cr"),
    pat_cr: base.pat_cr ?? attrNum(attrs, "pat_cr"),
    order_value_cr: orderCr,
    order_to_revenue_pct: base.order_to_revenue_pct ?? attrNum(attrs, "order_to_revenue_pct"),
    materiality_band: base.materiality_band ?? attrText(attrs, "materiality_band"),
  };
}

export function sectorProfileOf(item: NewsEventCard): SectorProfile {
  if (item.sector_profile) return item.sector_profile;
  const fromAttr = attrText(item.attributes, "sector_profile");
  if (fromAttr) return fromAttr as SectorProfile;
  const sector = (item.sector ?? "").toLowerCase();
  if (sector.includes("bank")) return "bank";
  if (sector.includes("nbfc") || sector.includes("finance")) return "nbfc";
  if (sector.includes("software") || sector.includes("it ")) return "it";
  if (sector.includes("pharma") || sector.includes("drug")) return "pharma";
  return "general";
}

export function sectorKpisOf(item: NewsEventCard): Record<string, number | null> {
  if (item.sector_kpis && Object.keys(item.sector_kpis).length) {
    return item.sector_kpis;
  }
  const profile = sectorProfileOf(item);
  const keys =
    profile === "bank" || profile === "nbfc"
      ? ["nim_pct", "gnpa_pct", "nnpa_pct", "casa_pct", "loan_growth_pct", "nii_yoy_pct"]
      : profile === "it"
        ? ["revenue_usd_yoy_pct", "ebit_margin_pct", "attrition_pct"]
        : profile === "pharma"
          ? ["ebitda_margin_pct"]
          : [];
  const out: Record<string, number | null> = {};
  for (const key of keys) {
    const v = attrNum(item.attributes, key);
    if (v != null) out[key] = v;
  }
  return out;
}

export function formatGrowth(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return formatPct(value);
}

export function formatCr(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `₹${formatNumber(value, { maximumFractionDigits: 1 })} Cr`;
}

export function sectorAnalysisTitle(profile: SectorProfile): string {
  switch (profile) {
    case "bank":
      return "Banking KPIs";
    case "nbfc":
      return "NBFC KPIs";
    case "it":
      return "IT KPIs";
    case "pharma":
      return "Pharma KPIs";
    default:
      return "Sector metrics";
  }
}

export function sectorAnalysisBlurb(
  profile: SectorProfile,
  kpis: Record<string, number | null>,
): string | null {
  if (profile === "bank" || profile === "nbfc") {
    const bits: string[] = [];
    if (kpis.nim_pct != null) bits.push(`NIM at ${kpis.nim_pct.toFixed(2)}%`);
    if (kpis.gnpa_pct != null) bits.push(`GNPA ${kpis.gnpa_pct.toFixed(2)}%`);
    if (kpis.nnpa_pct != null) bits.push(`NNPA ${kpis.nnpa_pct.toFixed(2)}%`);
    if (!bits.length) return null;
    const quality =
      kpis.gnpa_pct != null && kpis.gnpa_pct <= 2
        ? "Asset quality looks contained."
        : kpis.gnpa_pct != null
          ? "Watch asset quality closely."
          : "Review margins and asset quality.";
    return `${bits.join(", ")}. ${quality}`;
  }
  if (profile === "it") {
    const bits: string[] = [];
    if (kpis.revenue_usd_yoy_pct != null)
      bits.push(
        `USD revenue ${kpis.revenue_usd_yoy_pct >= 0 ? "+" : ""}${kpis.revenue_usd_yoy_pct.toFixed(1)}%`,
      );
    if (kpis.ebit_margin_pct != null) bits.push(`EBIT margin ${kpis.ebit_margin_pct.toFixed(1)}%`);
    if (kpis.attrition_pct != null) bits.push(`attrition ${kpis.attrition_pct.toFixed(1)}%`);
    return bits.length ? `${bits.join(", ")}.` : null;
  }
  return null;
}

export function hasFinancialMetrics(m: NewsMetrics): boolean {
  return (
    m.revenue_yoy_pct != null ||
    m.ebitda_yoy_pct != null ||
    m.pat_yoy_pct != null ||
    m.ocf_yoy_pct != null ||
    m.revenue_cr != null ||
    m.pat_cr != null
  );
}

export function hasOrderMetrics(m: NewsMetrics): boolean {
  return m.order_value_cr != null || m.order_to_revenue_pct != null;
}

export const KPI_LABELS: Record<string, string> = {
  nim_pct: "NIM",
  gnpa_pct: "GNPA",
  nnpa_pct: "NNPA",
  casa_pct: "CASA",
  loan_growth_pct: "Loan growth",
  nii_yoy_pct: "NII YoY",
  revenue_usd_yoy_pct: "USD rev YoY",
  ebit_margin_pct: "EBIT margin",
  attrition_pct: "Attrition",
  ebitda_margin_pct: "EBITDA margin",
};
