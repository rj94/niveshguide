export type SectorColumnId =
  | "rank"
  | "name"
  | "parent"
  | "score"
  | "state"
  | "change_1w"
  | "change_1m"
  | "change_3m"
  | "momentum"
  | "breadth"
  | "return_1m"
  | "names";

export const SECTOR_COLUMN_DEFS: {
  id: SectorColumnId;
  label: string;
  defaultVisible: boolean;
}[] = [
  { id: "rank", label: "Rank", defaultVisible: true },
  { id: "name", label: "Name", defaultVisible: true },
  { id: "parent", label: "Sector", defaultVisible: true },
  { id: "score", label: "Score", defaultVisible: true },
  { id: "state", label: "State", defaultVisible: true },
  { id: "change_1w", label: "1W Δ", defaultVisible: true },
  { id: "change_1m", label: "1M Δ", defaultVisible: true },
  { id: "change_3m", label: "3M Δ", defaultVisible: false },
  { id: "momentum", label: "Momentum", defaultVisible: false },
  { id: "breadth", label: "Breadth", defaultVisible: true },
  { id: "return_1m", label: "1M Ret", defaultVisible: true },
  { id: "names", label: "Names", defaultVisible: true },
];

export const SECTOR_PREF_KEY = "sectors.prefs.v1";

export type SectorPrefs = {
  sortBy: "rank" | "score" | "change_1m" | "change_1w" | "breadth" | "names";
  sortDir: "asc" | "desc";
  minConstituents: number;
  gainingOnly: boolean;
  showGaining: boolean;
  showSectors: boolean;
  showIndustries: boolean;
  columns: SectorColumnId[];
};

export const DEFAULT_SECTOR_PREFS: SectorPrefs = {
  sortBy: "rank",
  sortDir: "asc",
  minConstituents: 3,
  gainingOnly: false,
  showGaining: true,
  showSectors: true,
  showIndustries: true,
  columns: SECTOR_COLUMN_DEFS.filter((c) => c.defaultVisible).map((c) => c.id),
};

export function loadSectorPrefs(): SectorPrefs {
  if (typeof window === "undefined") return DEFAULT_SECTOR_PREFS;
  try {
    const raw = window.localStorage.getItem(SECTOR_PREF_KEY);
    if (!raw) return DEFAULT_SECTOR_PREFS;
    const parsed = JSON.parse(raw) as Partial<SectorPrefs>;
    const valid = new Set(SECTOR_COLUMN_DEFS.map((c) => c.id));
    const columns = (parsed.columns ?? DEFAULT_SECTOR_PREFS.columns).filter(
      (id): id is SectorColumnId => valid.has(id as SectorColumnId),
    );
    if (!columns.includes("name")) columns.unshift("name");
    return { ...DEFAULT_SECTOR_PREFS, ...parsed, columns };
  } catch {
    return DEFAULT_SECTOR_PREFS;
  }
}

export function saveSectorPrefs(prefs: SectorPrefs) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SECTOR_PREF_KEY, JSON.stringify(prefs));
}
