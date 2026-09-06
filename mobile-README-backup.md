# NSE Trend Desk — mobile (Expo)

Website stays in [`web/`](../web/). This package is the Android/iOS client on the same FastAPI backend.

**No signup / login.** Monetize with **Google AdMob**. The app does **not** scrape Screener.in or Google Sheets — it only reads the hosted API after the backend scheduler updates the database.

## When scaffolding Expo

```powershell
cd d:\Projects\Trade
npx create-expo-app@latest mobile --template tabs
```

Then:

1. Install ads: `npx expo install react-native-google-mobile-ads`
2. Set AdMob **app ID** in `app.json` / `app.config.js` (Android `GADApplicationIdentifier` / `com.google.android.gms.ads.APPLICATION_ID`).
3. Env (use [Google test banner IDs](https://developers.google.com/admob/android/test-ads) until Play Store):

```text
EXPO_PUBLIC_API_URL=https://your-api.example.com/api/v1
EXPO_PUBLIC_ADMOB_BANNER_ID=ca-app-pub-3940256099942544/6300978111
```

4. Show banner units on Dashboard, Momentum, and Stock detail (same placements as web AdSense).
5. For production: create an AdMob app linked to the Play Store listing, replace test IDs, and ship via EAS Build.

## Data

- Keep `SCHEDULER_ENABLED=true` on the API host so sheets sync and Screener imports refresh SQLite.
- Point the app at that host’s `EXPO_PUBLIC_API_URL` (not `127.0.0.1` on a physical phone).
