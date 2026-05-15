// Helpers used by route-change focus management. After SPA navigation, focus
// stays on whatever was clicked, leaving keyboard users tab-traversing from
// the previous page. Moving focus to the new page's <h1> (or <main>) on
// every nav fixes that.

export function focusPageHeading(): void {
  const target =
    document.querySelector<HTMLElement>('main h1') ??
    document.querySelector<HTMLElement>('main');

  if (!target) return;

  const hadTabIndex = target.hasAttribute('tabindex');
  if (!hadTabIndex) target.setAttribute('tabindex', '-1');

  target.focus({ preventScroll: false });

  // Don't leave a hanging tabindex on a non-interactive element forever.
  target.addEventListener(
    'blur',
    () => {
      if (!hadTabIndex) target.removeAttribute('tabindex');
    },
    { once: true },
  );
}

// Returns true when the event target is an editable element where global
// keyboard shortcuts should NOT fire.
export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.tagName === 'INPUT') return true;
  if (target.tagName === 'TEXTAREA') return true;
  if (target.tagName === 'SELECT') return true;
  if (target.isContentEditable) return true;
  return false;
}
