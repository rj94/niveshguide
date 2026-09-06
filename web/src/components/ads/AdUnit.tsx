"use client";

import { useEffect, useRef } from "react";

import { getAdSenseClient } from "@/lib/ads";
import { cn } from "@/lib/utils";

declare global {
  interface Window {
    adsbygoogle?: Record<string, unknown>[];
  }
}

type Props = {
  slot: string;
  className?: string;
};

/** Responsive display unit; renders nothing when client or slot env is missing. */
export function AdUnit({ slot, className }: Props) {
  const client = getAdSenseClient();
  const pushed = useRef(false);

  useEffect(() => {
    if (!client || !slot || pushed.current) return;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
      pushed.current = true;
    } catch {
      // Ad blockers / missing script — ignore
    }
  }, [client, slot]);

  if (!client || !slot) return null;

  return (
    <div
      className={cn(
        "min-h-[90px] w-full overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)]/40",
        className,
      )}
      aria-label="Advertisement"
    >
      <ins
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-client={client}
        data-ad-slot={slot}
        data-ad-format="auto"
        data-full-width-responsive="true"
      />
    </div>
  );
}
