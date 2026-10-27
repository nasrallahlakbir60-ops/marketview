interface EmptyStateProps {
  title: string;
  description?: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex min-h-[92px] flex-col items-center justify-center rounded-xl border border-dashed border-line/[0.1] bg-line/[0.02] px-4 py-6 text-center">
      <span className="text-xs font-medium text-muted">{title}</span>
      {description && <span className="mt-1 text-[11px] leading-5 text-subtle">{description}</span>}
    </div>
  );
}
