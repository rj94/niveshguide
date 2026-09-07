export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl animate-pulse space-y-6 px-4 py-8 sm:px-6">
      <div className="h-8 w-48 rounded bg-[var(--line)]" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 rounded-lg bg-[var(--line)]/60" />
        ))}
      </div>
      <div className="h-64 rounded-lg bg-[var(--line)]/40" />
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="h-48 rounded-lg bg-[var(--line)]/40" />
        <div className="h-48 rounded-lg bg-[var(--line)]/40" />
      </div>
    </div>
  );
}
