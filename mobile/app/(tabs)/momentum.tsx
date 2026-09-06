import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { screenStocks } from "../../src/api/client";
import { AdPlaceholder } from "../../src/components/AdPlaceholder";
import { MomentumRow } from "../../src/components/MomentumRow";
import { num } from "../../src/lib/format";
import { colors, spacing } from "../../src/theme";
import type { StockAnalysisRow } from "../../src/types/api";

export default function MomentumScreen() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const compact = width < 380;

  const [q, setQ] = useState("");
  const [minScore, setMinScore] = useState("");
  const [rows, setRows] = useState<StockAnalysisRow[]>([]);
  const [scanned, setScanned] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await screenStocks({
        q: q.trim() || undefined,
        exchange: "NSE",
        min_momentum_score: num(minScore) ?? undefined,
        sort_by: "momentum_score",
        sort_dir: "desc",
        limit: 400,
        scan_limit: 8000,
      });
      setRows(data.items);
      setScanned(data.scanned);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load momentum");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [q, minScore]);

  useEffect(() => {
    void load();
  }, []);

  const header = useMemo(
    () => (
      <View style={[styles.header, compact && styles.headerCompact]}>
        <Text style={styles.heading}>Momentum</Text>
        <Text style={styles.sub}>
          Ranked by momentum score · {rows.length} shown
          {scanned ? ` · scanned ${scanned.toLocaleString("en-IN")}` : ""}
        </Text>
        <AdPlaceholder label="Momentum" />
        <View style={styles.filters}>
          <TextInput
            value={q}
            onChangeText={setQ}
            placeholder="Symbol or name"
            placeholderTextColor={colors.inkMuted}
            style={styles.input}
            autoCapitalize="characters"
          />
          <TextInput
            value={minScore}
            onChangeText={setMinScore}
            placeholder="Min score"
            placeholderTextColor={colors.inkMuted}
            keyboardType="numeric"
            style={[styles.input, styles.inputNarrow]}
          />
          <Pressable onPress={() => void load()} style={styles.applyBtn}>
            <Text style={styles.applyText}>Apply</Text>
          </Pressable>
        </View>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {loading ? (
          <ActivityIndicator color={colors.accent} style={{ marginVertical: 12 }} />
        ) : null}
      </View>
    ),
    [compact, q, minScore, rows.length, scanned, error, loading, load],
  );

  return (
    <SafeAreaView style={styles.safe} edges={["left", "right"]}>
      <FlatList
        data={rows}
        keyExtractor={(item) => item.symbol}
        ListHeaderComponent={header}
        renderItem={({ item, index }) => (
          <MomentumRow
            row={item}
            rank={index + 1}
            onPress={() =>
              router.push(`/stock/${encodeURIComponent(item.symbol)}`)
            }
          />
        )}
        ListEmptyComponent={
          !loading ? (
            <Text style={styles.empty}>No stocks match these filters.</Text>
          ) : null
        }
        contentContainerStyle={{ paddingBottom: 32 }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    padding: spacing.lg,
    gap: spacing.sm,
  },
  headerCompact: {
    paddingHorizontal: spacing.md,
  },
  heading: {
    color: colors.ink,
    fontSize: 28,
    fontWeight: "800",
  },
  sub: { color: colors.inkMuted, fontSize: 13, marginBottom: 4 },
  filters: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  input: {
    flexGrow: 1,
    minWidth: 120,
    minHeight: 44,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.surfaceMuted,
    color: colors.ink,
    paddingHorizontal: 12,
  },
  inputNarrow: {
    flexGrow: 0,
    width: 100,
  },
  applyBtn: {
    minHeight: 44,
    minWidth: 72,
    borderRadius: 10,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 14,
  },
  applyText: { color: "#fff", fontWeight: "700" },
  error: { color: colors.down, fontSize: 13, marginTop: 8 },
  empty: {
    color: colors.inkMuted,
    textAlign: "center",
    padding: 24,
  },
});
