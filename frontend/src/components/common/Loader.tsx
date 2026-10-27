interface LoaderProps {
  label?: string;
  className?: string;
}

export function Loader({ label = "Chargement...", className = "" }: LoaderProps) {
  return (
    <div className={`flex items-center justify-center gap-3 py-8 text-sm text-muted ${className}`} role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line/20 border-t-accent" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
