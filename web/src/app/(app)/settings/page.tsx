import { ContrastControl } from "@/components/theme/ContrastControl";

export default function SettingsPage() {
  return (
    <div className="page-shell mx-auto max-w-3xl space-y-6 py-8">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--accent)]">
          Preferences
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">Settings</h1>
        <p className="mt-2 max-w-xl text-sm text-[var(--ink-soft)]">
          Choose a color contrast that is comfortable to read. The same look is used on the home
          page and every other screen.
        </p>
      </header>
      <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Color contrast</h2>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Dark matches the NiveshGuide home theme. Light brightens the pages. High contrast
          strengthens text and borders.
        </p>
        <div className="mt-4">
          <ContrastControl compact={false} />
        </div>
      </section>
    </div>
  );
}
