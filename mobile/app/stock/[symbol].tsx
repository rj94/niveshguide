import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { Stack, useLocalSearchParams } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { getStock } from "../../src/api/client";
import { AdPlaceholder } from "../../src/components/AdPlaceholder";
import { SectionCard } from "../../src/components/SectionCard";
import { formatPct, formatPrice, num } from "../../src/lib/format";
import { colors, spacing } from "../../src/theme";
import type { StockDetail } from "../../src/types/api";

export default function StockScreen() {
  const { symbol } = useLocalSearchParams<{ symbol: string }>();
  const { width } = useWindowDimensions();
  const compact = width < 380;

  const [stock, setStock] = useState<StockDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await getStock(String(symbol), { exchange: "NSE" });
        if (!cancelled) {
          setStock(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load stock");
          setStock(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  const change = stock?.quote.change_pct ?? null;
  const t = stock?.technicals;

  return (
    <SafeAreaView style={styles.safe} edges={["left", "right", "bottom"]}>
      <Stack.Screen options={{ title: String(symbol || "Stock").toUpperCase() }} />
      <ScrollView
        contentContainerStyle={[styles.content, compact && styles.contentCompact]}
      >
        {loading ? (
          <ActivityIndicator color={colors.accent} style={{ marginTop: 24 }} />
        ) : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}

        {stock ? (
          <>
            <Text style={styles.symbol}>{stock.symbol}</Text>
            <Text style={styles.name}>{stock.company_name}</Text>
            <Text style={styles.meta}>
              {stock.exchange}
              {stock.sector ? ` · ${stock.sector}` : ""}
              {stock.industry ? ` · ${stock.industry}` : ""}
            </Text>

            <View style={styles.quoteRow}>
              <Text style={styles.price}>{formatPrice(stock.quote.price)}</Text>
              <Text
                style={[
                  styles.change,
                  change != null && change >= 0 ? styles.up : styles.down,
                ]}
              >
                {formatPct(change)}
              </Text>
            </View>

            <AdPlaceholder label="Stock" />

            <SectionCard title="Momentum">
              <Metric
                label="Score"
                value={
                  num(stock.scores.momentum)?.toFixed(1) ??
                  (t?.momentum_score != null ? String(t.momentum_score) : "—")
                }
              />
              <Metric
                label="Category"
                value={
                  stock.scores.momentum_category ||
                  t?.momentum_category ||
                  "—"
                }
              />
              <Metric
                label="Acceleration"
                value={
                  num(stock.scores.momentum_acceleration)?.toFixed(2) ??
                  (t?.momentum_acceleration != null
                    ? String(t.momentum_acceleration)
                    : "—")
                }
              />
              <Metric label="Trend" value={t?.trend ?? "—"} />
            </SectionCard>

            <SectionCard title="Returns">
              <Metric label="1M" value={formatPct(t?.return_1m_pct ?? null)} />
              <Metric label="3M" value={formatPct(t?.return_3m_pct ?? null)} />
              <Metric label="6M" value={formatPct(t?.return_6m_pct ?? null)} />
              <Metric label="1Y" value={formatPct(t?.return_1y_pct ?? null)} />
            </SectionCard>

            <SectionCard title="Score breakdown">
              <Metric label="Return" value={stock.scores.return_score ?? "—"} />
              <Metric label="DMA" value={stock.scores.dma_score ?? "—"} />
              <Metric label="Volume" value={stock.scores.volume_score ?? "—"} />
              <Metric label="Results" value={stock.scores.result_score ?? "—"} />
              <Metric
                label="Sector"
                value={stock.scores.sector_strength ?? "—"}
              />
            </SectionCard>
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, paddingBottom: 40 },
  contentCompact: { paddingHorizontal: spacing.md },
  symbol: { color: colors.ink, fontSize: 32, fontWeight: "800" },
  name: { color: colors.inkSoft, fontSize: 15, marginTop: 4 },
  meta: { color: colors.inkMuted, fontSize: 12, marginTop: 6, marginBottom: 12 },
  quoteRow: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: 12,
    marginBottom: spacing.md,
    flexWrap: "wrap",
  },
  price: {
    color: colors.ink,
    fontSize: 36,
    fontWeight: "800",
    fontVariant: ["tabular-nums"],
  },
  change: { fontSize: 18, fontWeight: "700", fontVariant: ["tabular-nums"] },
  up: { color: colors.up },
  down: { color: colors.down },
  metric: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
    gap: 12,
  },
  metricLabel: { color: colors.inkMuted, fontSize: 13 },
  metricValue: {
    color: colors.ink,
    fontSize: 13,
    fontWeight: "600",
    flexShrink: 1,
    textAlign: "right",
  },
  error: { color: colors.down, marginTop: 16 },
});
