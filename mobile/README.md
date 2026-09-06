# NiveshGuide — mobile (Expo)

Phone client for the same FastAPI backend as [`web/`](../web/). **No signup.** Scraping stays on the server; this app only reads the API.

## SDK eligibility (majority of phones)

| Platform | Target |
| --- | --- |
| Android | `minSdkVersion` **24** (Android 7.0+) via `expo-build-properties` |
| iOS | deployment target **16.4+** (Expo SDK 57) |
| Form factor | Portrait phones (responsive from ~320–430+ logical px) |

## Quick start (Expo Go)

```powershell
# Terminal 1 — API reachable on LAN
cd d:\Projects\Trade\backend
.\.venv\Scripts\Activate.ps1
python -m cli serve --host 0.0.0.0 --port 8011

# Terminal 2 — Expo
cd d:\Projects\Trade\mobile
copy .env.example .env
npm start
```

- Scan the QR code with **Expo Go** on a physical phone (same Wi‑Fi).
- In **Settings**, set API URL to `http://<YOUR-PC-LAN-IP>:8011/api/v1` (not `127.0.0.1`).
- Android emulator can use default `http://10.0.2.2:8011/api/v1`.

## Screens

- **Dashboard** — indices, sector ETFs, top momentum, sector strength (30s poll)
- **Momentum** — ranked list + filters → stock detail
- **Stock** — quote, momentum, returns, score breakdown
- **Settings** — API base URL + AdMob notes

## Ads

Expo Go shows an **ad placeholder** strip (native AdMob is not available in Expo Go).

For Play Store / EAS builds later:

1. Add `react-native-google-mobile-ads` and AdMob app IDs.
2. Set `EXPO_PUBLIC_USE_NATIVE_ADMOB=true` and real banner IDs.
3. Replace the placeholder component with a real banner.

Test banner ID (Google): `ca-app-pub-3940256099942544/6300978111`

## Multi-phone preview / test matrix

| Device | How to preview |
| --- | --- |
| Small (~360×640) | Android Studio AVD “Pixel 3a” or similar → `npm run android` |
| Common (~393×851) | Pixel 6 / 7 AVD |
| Large (~430×932) | Pixel 8 Pro AVD or large physical phone |
| Physical Android | Expo Go + QR on same Wi‑Fi |
| Optional iOS | Expo Go on iPhone |

### Manual checklist

- [ ] Dashboard scrolls on a small phone; chips wrap without horizontal overflow
- [ ] Momentum filters usable (44px+ tap targets); list scrolls
- [ ] Stock header + quote not clipped; ad placeholder visible
- [ ] Settings save persists API URL after reload
- [ ] Wrong API URL shows a clear error pointing to Settings

### Emulator tip (Windows)

Install Android Studio → Device Manager → create Pixel 3a + Pixel 7 → start emulator → from `mobile/`: `npx expo start --android`.

## Env

See [`.env.example`](.env.example):

```text
EXPO_PUBLIC_API_URL=http://10.0.2.2:8011/api/v1
EXPO_PUBLIC_ADMOB_BANNER_ID=ca-app-pub-3940256099942544/6300978111
EXPO_PUBLIC_USE_NATIVE_ADMOB=false
```

## CORS / LAN

Native Expo Go does not rely on browser CORS. For Expo web / LAN browsers, the API allows private network origins via regex in [`backend/main.py`](../backend/main.py). Bind the API with `--host 0.0.0.0`.
