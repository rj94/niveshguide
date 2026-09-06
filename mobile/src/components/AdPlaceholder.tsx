import { StyleSheet, Text, View, useWindowDimensions } from "react-native";

import { colors, spacing } from "../theme";

/**
 * Expo Go cannot load native AdMob. Shows a labeled strip so layout
 * matches production banner height across phone sizes.
 * Set EXPO_PUBLIC_USE_NATIVE_ADMOB=true in a custom/dev build later.
 */
export function AdPlaceholder({ label = "Ad" }: { label?: string }) {
  const { width } = useWindowDimensions();
  const compact = width < 380;

  return (
    <View
      style={[styles.wrap, compact && styles.wrapCompact]}
      accessibilityLabel="Advertisement placeholder"
    >
      <Text style={styles.kicker}>Sponsored</Text>
      <Text style={styles.title}>
        {label} · AdMob banner (Expo Go placeholder)
      </Text>
      <Text style={styles.hint}>
        Real ads appear in a Play Store / EAS build with AdMob IDs.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    minHeight: 90,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.adBg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    justifyContent: "center",
  },
  wrapCompact: {
    minHeight: 80,
    paddingVertical: spacing.sm,
  },
  kicker: {
    color: colors.inkMuted,
    fontSize: 10,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    marginBottom: 4,
  },
  title: {
    color: colors.inkSoft,
    fontSize: 13,
    fontWeight: "600",
  },
  hint: {
    color: colors.inkMuted,
    fontSize: 11,
    marginTop: 4,
  },
});
