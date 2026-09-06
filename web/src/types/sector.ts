export type StrengthRow = {
  name: string;
  parent_sector: string | null;
  as_of: string | null;
  strength_score: string | null;
  momentum_score: string | null;
  relative_strength_score: string | null;
  breadth_score: string | null;
  risk_score: string | null;
  rank: number | null;
  rank_change: number | null;
  score_change_1w: string | null;
  score_change_1m: string | null;
  score_change_3m: string | null;
  score_1w_ago: string | null;
  score_1m_ago: string | null;
  score_3m_ago: string | null;
  rotation_state: string | null;
  is_gaining_strength: boolean | null;
  constituent_count: number | null;
  return_1m: string | null;
  return_3m: string | null;
  return_3m_cw: string | null;
  return_3m_ew: string | null;
  return_3m_index: string | null;
  return_3m_source: "index" | "cap_weight" | "equal_weight" | string | null;
  above_50dma_pct: string | null;
  sector_name?: string | null;
  sector_strength_score?: string | null;
  industry_name?: string | null;
  industry_strength_score?: string | null;
};

export type SectorScoreRow = StrengthRow & {
  sector_name?: string | null;
  sector_strength_score?: string | null;
};
export type IndustryScoreRow = StrengthRow & {
  industry_name?: string | null;
  industry_strength_score?: string | null;
};

export type SectorListResponse = {
  items: SectorScoreRow[];
  industries: IndustryScoreRow[];
  gaining: SectorScoreRow[];
  as_of: string | null;
};
