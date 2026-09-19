"use client";

import { useEffect, useState } from "react";
import { Contrast, Moon, Sun } from "lucide-react";

import {
  applyContrastTheme,
  readStoredTheme,
  THEME_EVENT,
  THEME_OPTIONS,
  type ContrastTheme,
} from "@/lib/theme";
import { cn } from "@/lib/utils";

const ICONS = {
  dark: Moon,
  light: Sun,
  high: Contrast,
} as const;

type Props = {
  compact?: boolean;
};

export function ContrastControl({ compact = true }: Props) {
  const [theme, setTheme] = useState<ContrastTheme>("dark");

  useEffect(() => {
    const sync = () => setTheme(readStoredTheme());
    sync();
    window.addEventListener(THEME_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(THEME_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  function choose(next: ContrastTheme) {
    applyContrastTheme(next);
    setTheme(next);
  }

  if (!compact) {
    return (
      <div className="grid gap-2 sm:grid-cols-3">
        {THEME_OPTIONS.map((option) => {
          const Icon = ICONS[option.id];
          const active = theme === option.id;
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => choose(option.id)}
              className={cn(
                "rounded-xl border px-3 py-3 text-left transition",
                active
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--line)] bg-[var(--surface)] hover:border-[var(--line-strong)]",
              )}
            >
              <Icon className="h-4 w-4 text-[var(--accent)]" />
              <p className="mt-2 text-sm font-semibold text-[var(--ink)]">{option.label}</p>
              <p className="mt-0.5 text-xs text-[var(--ink-muted)]">{option.hint}</p>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div
      role="radiogroup"
      aria-label="Color contrast"
      className="flex items-center rounded-lg border border-[var(--line)] bg-[var(--surface-muted)] p-0.5"
    >
      {THEME_OPTIONS.map((option) => {
        const Icon = ICONS[option.id];
        const active = theme === option.id;
        return (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={active}
            title={option.hint}
            onClick={() => choose(option.id)}
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-[11px] font-semibold transition sm:px-2.5",
              active
                ? "bg-[var(--accent)] text-[var(--accent-ink)]"
                : "text-[var(--ink-soft)] hover:text-[var(--ink)]",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
