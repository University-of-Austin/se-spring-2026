import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { isEditableTarget } from '../lib/focus';

// App-wide keyboard shortcuts:
//   /  → focus search input (if any on current page)
//   n  → navigate to / and focus the compose textarea
//   ?  → open the keyboard help overlay
// All guarded against editable targets so they don't steal keys mid-typing.
export function useGlobalShortcuts({ onHelp }: { onHelp: () => void }): void {
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isEditableTarget(e.target)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === '/') {
        const search = document.querySelector<HTMLInputElement>('[data-shortcut="search"]');
        if (search) {
          e.preventDefault();
          search.focus();
          search.select();
        }
        return;
      }

      if (e.key === 'n') {
        e.preventDefault();
        navigate('/');
        // Defer one tick so the FeedPage mounts before we try to focus
        setTimeout(() => {
          const textarea = document.querySelector<HTMLTextAreaElement>('[data-shortcut="compose"]');
          textarea?.focus();
        }, 0);
        return;
      }

      if (e.key === '?') {
        e.preventDefault();
        onHelp();
        return;
      }
    };

    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navigate, onHelp]);
}
