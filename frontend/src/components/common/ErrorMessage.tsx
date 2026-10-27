interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorMessage({ message, onRetry, className = "" }: ErrorMessageProps) {
  return (
    <div
      className={`flex flex-col gap-3 rounded-xl border border-rose-500/25 bg-rose-500/[0.07] p-4 text-sm text-rose-700 dark:text-rose-200 sm:flex-row sm:items-center sm:justify-between ${className}`}
      role="alert"
    >
      <span>{message}</span>
      {onRetry && (
        <button
          className="shrink-0 rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs font-medium transition hover:bg-rose-500/10"
          onClick={onRetry}
          type="button"
        >
          Réessayer
        </button>
      )}
    </div>
  );
}
