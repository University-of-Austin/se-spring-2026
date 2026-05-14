import { type ApiError, formatDetail } from "@/api/types";

export default function ErrorBox({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div role="alert" className="border border-red-300 bg-red-50 text-red-900 px-3 py-2 rounded text-sm flex items-start gap-3">
      <span className="flex-1">
        <span className="font-medium">Error {error.status}.</span> {formatDetail(error.detail)}
      </span>
      {onRetry && (
        <button onClick={onRetry} className="underline">Retry</button>
      )}
    </div>
  );
}
