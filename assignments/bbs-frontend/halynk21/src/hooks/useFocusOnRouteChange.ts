import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { focusPageHeading } from '../lib/focus';

// SPA navigation doesn't move focus by default — keyboard users keep tabbing
// from wherever they were on the previous page. This hook moves focus to the
// new page's <h1> (or <main>) on every navigation.
export function useFocusOnRouteChange(): void {
  const location = useLocation();
  useEffect(() => {
    focusPageHeading();
  }, [location.pathname]);
}
