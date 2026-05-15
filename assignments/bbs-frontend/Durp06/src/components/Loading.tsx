interface Props {
  label?: string;
}

export function Loading({ label = 'Loading…' }: Props) {
  return (
    <div className="loading" role="status" aria-label={label}>
      <span className="loading__spinner" aria-hidden="true" />
      <span className="loading__label">{label}</span>
    </div>
  );
}
