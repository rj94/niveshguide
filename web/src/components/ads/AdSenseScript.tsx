import Script from "next/script";

import { getAdSenseClient } from "@/lib/ads";

/** Load Google AdSense once when NEXT_PUBLIC_ADSENSE_CLIENT is set. */
export function AdSenseScript() {
  const client = getAdSenseClient();
  if (!client) return null;

  return (
    <Script
      id="adsense-loader"
      async
      src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(client)}`}
      crossOrigin="anonymous"
      strategy="afterInteractive"
    />
  );
}
