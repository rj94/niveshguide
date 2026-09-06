import { Pressable, StyleSheet, Text, View } from "react-native";

import { formatPct, formatPrice, num } from "../lib/format";
import { colors, spacing } from "../theme";
import type { StockAnalysisRow } from "../types/api";

type Props = {
  row: StockAnalysisRow;
  rank: number;
  onPress: () => void;
};

export function MomentumRow({ row, rank, onPress }: Props) {
  const change = row.change_pct;
  const score = num(row.momentum_score);

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
      accessibilityRole="button"
    >
      <Text style={styles.rank}>{rank}</Text>
      <View style={styles.main}>
        <Text style={styles.symbol} numberOfLines={1}>
          {row.symbol}
        </Text>
        <Text style={styles.meta} numberOfLines={1}>
          {row.sector || row.company_name || "—"}
        </Text>
      </View>
      <View style={styles.right}>
        <Text style={styles.score}>{score != null ? score.toFixed(0) : "—"}</Text>
        <Text
          style={[
            styles.pct,
            change != null && change > 0 ? styles.up : null,
            change != null && change < 0 ? styles.down : null,
          ]}
        >
          {formatPct(change)}
        </Text>
        <Text style={styles.ltp}>{formatPrice(row.ltp)}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    minHeight: 56,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
    backgroundColor: colors.surface,
  },
  pressed: {
    backgroundColor: colors.surfaceMuted,
  },
  rank: {
    width: 28,
    color: colors.inkMuted,
    fontSize: 12,
    fontVariant: ["tabular-nums"],
  },
  main: {
    flex: 1,
    minWidth: 0,
    paddingRight: spacing.sm,
  },
  symbol: {
    color: colors.ink,
    fontSize: 15,
    fontWeight: "700",
  },
  meta: {
    color: colors.inkMuted,
    fontSize: 12,
    marginTop: 2,
  },
  right: {
    alignItems: "flex-end",
    minWidth: 72,
  },
  score: {
    color: colors.accent,
    fontSize: 16,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  pct: {
    color: colors.inkMuted,
    fontSize: 12,
    marginTop: 2,
    fontVariant: ["tabular-nums"],
  },
  ltp: {
    color: colors.inkSoft,
    fontSize: 11,
    marginTop: 2,
    fontVariant: ["tabular-nums"],
  },
  up: { color: colors.up },
  down: { color: colors.down },
});
