import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { getMarketsOverview, listSectors, screenStocks } from "../../src/api/client";
import { AdPlaceholder } from "../../src/components/AdPlaceholder";
import { SectionCard } from "../../src/components/SectionCard";
import { formatPct, formatPrice, num } from "../../src/lib/format";
import { colors, spacing } from "../../src/theme";
import type {
  MarketQuoteCard,
  SectorScoreRow,
  StockAnalysisRow,
} from "../../src/types/api";

export default function DashboardScreen() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const compact = width < 380;

  const [indices, setIndices] = useState<MarketQuoteCard[]>([]);
  const [etfs, setEtfs] = useState<MarketQuoteCard[]>([]);
  const [leaders, setLeaders] = useState<StockAnalysisRow[]>([]);
  const [sectors, setSectors] = useState<SectorScoreRow[]>([]);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [overview, momentum, sectorData] = await Promise.all([
        getMarketsOverview(),
        screenStocks({
          exchange: "NSE",
          sort_by: "momentum_score",
          sort_dir: "desc",
          limit: 12,
          scan_limit: 4000,
        }),
        listSectors({ limit: 8, min_constituents: 3 }).catch(() => ({ items: [] })),
      ]);
      setIndices(overview.indices ?? []);
      setEtfs((overview.sector_etfs ?? []).slice(0, compact ? 4 : 6));
      setLeaders(momentum.items ?? []);
      setSectors(sectorData.items ?? []);
      setAsOf(overview.as_of);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [compact]);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 30_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["left", "right"]}>
      <ScrollView
        contentContainerStyle={[styles.content, compact && styles.contentCompact]}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              void load();
            }}
            tintColor={colors.accent}
          />
        }
      >
        <Text style={styles.kicker}>NiveshGuide</Text>
        <Text style={styles.heading}>Dashboard</Text>
        <Text style={styles.sub}>
          {asOf ? `Market snapshot · ${asOf}` : "Pull to refresh · polls every 30s"}
        </Text>

        <AdPlaceholder label="Dashboard" />

        {loading ? (
          <ActivityIndicator color={colors.accent} style={{ marginTop: 24 }} />
        ) : null}

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
            <Text style={styles.errorHint}>
              Open Settings and set your PC LAN API URL (not 127.0.0.1 on a phone).
            </Text>
          </View>
        ) : null}

        <SectionCard title="Indices">
          <View style={styles.chipRow}>
            {(indices.length ? indices : []).slice(0, 5).map((idx) => {
              const pct = idx.change_pct;
              return (
                <View key={idx.id || idx.symbol} style={[styles.chip, compact && styles.chipFull]}>
                  <Text style={styles.chipName} numberOfLines={1}>
                    {idx.name || idx.symbol}
                  </Text>
                  <Text style={styles.chipValue}>{formatPrice(idx.value)}</Text>
                  <Text
                    style={[
                      styles.chipPct,
                      pct != null && pct >= 0 ? styles.up : styles.down,
                    ]}
                  >
                    {formatPct(pct)}
                  </Text>
                </View>
              );
            })}
            {!indices.length && !loading ? (
              <Text style={styles.empty}>No index quotes yet.</Text>
            ) : null}
          </View>
        </SectionCard>

        <SectionCard title="Sector ETFs">
          {etfs.map((etf) => (
            <View key={etf.symbol} style={styles.listRow}>
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={styles.rowTitle} numberOfLines={1}>
                  {etf.symbol}
                </Text>
                <Text style={styles.rowMeta} numberOfLines={1}>
                  {etf.name}
                </Text>
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <Text style={styles.rowValue}>{formatPrice(etf.value)}</Text>
                <Text
                  style={[
                    styles.chipPct,
                    etf.change_pct != null && etf.change_pct >= 0
                      ? styles.up
                      : styles.down,
                  ]}
                >
                  {formatPct(etf.change_pct)}
                </Text>
              </View>
            </View>
          ))}
          {!etfs.length && !loading ? (
            <Text style={styles.empty}>No ETF quotes.</Text>
          ) : null}
        </SectionCard>

        <SectionCard title="Top momentum">
          {leaders.map((row, i) => (
            <Pressable
              key={row.symbol}
              onPress={() => router.push(`/stock/${encodeURIComponent(row.symbol)}`)}
              style={styles.listRow}
            >
              <Text style={styles.rank}>{i + 1}</Text>
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={styles.rowTitle}>{row.symbol}</Text>
                <Text style={styles.rowMeta} numberOfLines={1}>
                  {row.momentum_category || row.sector || "—"}
                </Text>
              </View>
              <Text style={styles.score}>
                {num(row.momentum_score)?.toFixed(0) ?? "—"}
              </Text>
            </Pressable>
          ))}
        </SectionCard>

        <SectionCard title="Sector strength">
          {sectors.map((s) => (
            <View key={s.name} style={styles.listRow}>
              <Text style={[styles.rowTitle, { flex: 1 }]} numberOfLines={1}>
                {s.name}
              </Text>
              <Text style={styles.rowValue}>{formatNumberSafe(s.score)}</Text>
            </View>
          ))}
          {!sectors.length && !loading ? (
            <Text style={styles.empty}>No sector scores.</Text>
          ) : null}
        </SectionCard>
      </ScrollView>
    </SafeAreaView>
  );
}

function formatNumberSafe(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return String(value);
  return n.toFixed(1);
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: {
    padding: spacing.lg,
    paddingBottom: 40,
  },
  contentCompact: {
    paddingHorizontal: spacing.md,
  },
  kicker: {
    color: colors.accent,
    fontSize: 11,
    letterSpacing: 1.4,
    textTransform: "uppercase",
    fontWeight: "700",
  },
  heading: {
    color: colors.ink,
    fontSize: 28,
    fontWeight: "800",
    marginTop: 4,
  },
  sub: {
    color: colors.inkMuted,
    fontSize: 13,
    marginBottom: spacing.md,
    marginTop: 4,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  chip: {
    width: "47%",
    minWidth: 140,
    flexGrow: 1,
    backgroundColor: colors.surfaceMuted,
    borderRadius: 10,
    padding: spacing.sm,
  },
  chipFull: {
    width: "100%",
  },
  chipName: { color: colors.inkMuted, fontSize: 11 },
  chipValue: {
    color: colors.ink,
    fontSize: 16,
    fontWeight: "700",
    marginTop: 4,
    fontVariant: ["tabular-nums"],
  },
  chipPct: { fontSize: 12, marginTop: 2, fontVariant: ["tabular-nums"] },
  listRow: {
    flexDirection: "row",
    alignItems: "center",
    minHeight: 48,
    paddingVertical: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
    gap: 8,
  },
  rank: { width: 22, color: colors.inkMuted, fontSize: 12 },
  rowTitle: { color: colors.ink, fontSize: 14, fontWeight: "700" },
  rowMeta: { color: colors.inkMuted, fontSize: 12, marginTop: 2 },
  rowValue: { color: colors.inkSoft, fontSize: 13, fontVariant: ["tabular-nums"] },
  score: {
    color: colors.accent,
    fontWeight: "800",
    fontSize: 16,
    minWidth: 36,
    textAlign: "right",
  },
  empty: { color: colors.inkMuted, fontSize: 13, paddingVertical: 8 },
  up: { color: colors.up },
  down: { color: colors.down },
  errorBox: {
    backgroundColor: "rgba(239,68,68,0.12)",
    borderColor: "rgba(239,68,68,0.4)",
    borderWidth: 1,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  errorText: { color: colors.down, fontSize: 13 },
  errorHint: { color: colors.inkMuted, fontSize: 12, marginTop: 6 },
});
