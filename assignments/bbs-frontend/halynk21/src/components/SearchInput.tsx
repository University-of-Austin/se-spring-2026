type Props = {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
};

// Plain controlled input. Debouncing is the parent's job (so the parent owns
// what's "committed" vs what's typed).
export function SearchInput({ value, onChange, placeholder = 'Search posts...' }: Props) {
  return (
    <div className="search-input">
      <label className="sr-only" htmlFor="feed-search">Search posts</label>
      <input
        id="feed-search"
        type="search"
        data-shortcut="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}
