type Props = {
  title: string;
  description: string;
};

export function PlaceholderPage({ title, description }: Props) {
  return (
    <div className="page-shell mx-auto flex max-w-3xl flex-col py-12">
      <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--accent)]">
        Coming soon
      </p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--ink)]">
        {title}
      </h1>
      <p className="mt-3 max-w-xl text-[var(--ink-soft)]">{description}</p>
    </div>
  );
}
