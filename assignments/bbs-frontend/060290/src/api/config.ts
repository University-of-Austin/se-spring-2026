export function getApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
  return raw.replace(/\/+$/, '')
}
