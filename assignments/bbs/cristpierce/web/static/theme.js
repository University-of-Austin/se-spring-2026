// Theme toggle — persists to localStorage
(function() {
  const html = document.documentElement;
  const saved = localStorage.getItem('bbs-theme');
  if (saved) html.setAttribute('data-theme', saved);

  window.toggleTheme = function() {
    const current = html.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', next);
    localStorage.setItem('bbs-theme', next);
    const btn = document.querySelector('.theme-toggle');
    if (btn) btn.textContent = next === 'light' ? '[ DARK ]' : '[ LIGHT ]';
  };

  // Update button text on load
  document.addEventListener('DOMContentLoaded', function() {
    const btn = document.querySelector('.theme-toggle');
    if (btn) {
      const theme = html.getAttribute('data-theme') || 'dark';
      btn.textContent = theme === 'light' ? '[ DARK ]' : '[ LIGHT ]';
    }
  });
})();
