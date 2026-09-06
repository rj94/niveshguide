import { useEffect, useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  DEFAULT_API_BASE,
  getApiBase,
  getAdMobBannerId,
  setApiBase,
} from "../../src/api/config";
import { AdPlaceholder } from "../../src/components/AdPlaceholder";
import { colors, spacing } from "../../src/theme";

export default function SettingsScreen() {
  const { width } = useWindowDimensions();
  const compact = width < 380;
  const [url, setUrl] = useState(DEFAULT_API_BASE);
  const [saved, setSaved] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void getApiBase().then((base) => {
      setUrl(base);
      setSaved(base);
    });
  }, []);

  async function onSave() {
    await setApiBase(url);
    setSaved(url.trim().replace(/\/$/, ""));
    setMessage("Saved. Pull to refresh on Dashboard / Momentum.");
  }

  return (
    <SafeAreaView style={styles.safe} edges={["left", "right"]}>
      <ScrollView
        contentContainerStyle={[styles.content, compact && styles.contentCompact]}
      >
        <Text style={styles.heading}>Settings</Text>
        <Text style={styles.sub}>
          No signup. Point the app at your FastAPI host. Physical phones cannot use
          127.0.0.1 — use your PC LAN IP.
        </Text>

        <AdPlaceholder label="Settings" />

        <Text style={styles.label}>API base URL</Text>
        <TextInput
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="http://192.168.x.x:8011/api/v1"
          placeholderTextColor={colors.inkMuted}
          style={styles.input}
        />
        <Text style={styles.hint}>
          Android emulator default: http://10.0.2.2:8011/api/v1{"\n"}
          Physical phone example: http://192.168.1.10:8011/api/v1{"\n"}
          Serve API with: python -m cli serve --host 0.0.0.0 --port 8011
        </Text>

        <Pressable onPress={() => void onSave()} style={styles.btn}>
          <Text style={styles.btnText}>Save API URL</Text>
        </Pressable>

        {message ? <Text style={styles.ok}>{message}</Text> : null}
        {saved ? (
          <Text style={styles.meta}>Current: {saved}</Text>
        ) : null}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Ads (AdMob)</Text>
          <Text style={styles.meta}>
            Banner test ID: {getAdMobBannerId()}
          </Text>
          <Text style={styles.hint}>
            Expo Go shows the placeholder strip. Native AdMob needs an EAS / Play
            Store build with EXPO_PUBLIC_USE_NATIVE_ADMOB=true.
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>SDK targets</Text>
          <Text style={styles.meta}>
            Android minSdk 24 · iOS 16.4+ · phones (portrait)
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, gap: spacing.sm, paddingBottom: 40 },
  contentCompact: { paddingHorizontal: spacing.md },
  heading: { color: colors.ink, fontSize: 28, fontWeight: "800" },
  sub: { color: colors.inkMuted, fontSize: 13, marginBottom: spacing.sm },
  label: {
    color: colors.inkSoft,
    fontSize: 12,
    fontWeight: "700",
    marginTop: spacing.md,
  },
  input: {
    minHeight: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.surfaceMuted,
    color: colors.ink,
    paddingHorizontal: 12,
    marginTop: 6,
  },
  hint: { color: colors.inkMuted, fontSize: 12, lineHeight: 18, marginTop: 8 },
  btn: {
    marginTop: spacing.md,
    minHeight: 48,
    borderRadius: 12,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  btnText: { color: "#fff", fontWeight: "800" },
  ok: { color: colors.up, marginTop: 8, fontSize: 13 },
  meta: { color: colors.inkSoft, fontSize: 12, marginTop: 6 },
  card: {
    marginTop: spacing.lg,
    padding: spacing.md,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.surface,
  },
  cardTitle: { color: colors.ink, fontWeight: "700", fontSize: 14 },
});
