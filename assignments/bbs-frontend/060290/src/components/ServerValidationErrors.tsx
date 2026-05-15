import './ServerValidationErrors.css'

type DetailItem = {
  loc?: unknown[]
  msg?: string
  type?: string
}

function linesFromDetail(detail: unknown): string[] {
  if (typeof detail === 'string') {
    return [detail]
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) {
        const d = item as DetailItem
        const loc =
          Array.isArray(d.loc) && d.loc.length
            ? `${d.loc.filter((x) => x !== 'body').join(' › ')}: `
            : ''
        return `${loc}${d.msg ?? JSON.stringify(item)}`
      }
      return JSON.stringify(item)
    })
  }
  if (detail && typeof detail === 'object') {
    return [JSON.stringify(detail)]
  }
  return []
}

export function ServerValidationErrors({ body }: { body: unknown }) {
  if (!body || typeof body !== 'object' || !('detail' in body)) {
    return null
  }
  const lines = linesFromDetail((body as { detail: unknown }).detail)
  if (!lines.length) {
    return null
  }
  return (
    <ul className="validation-errors">
      {lines.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  )
}
