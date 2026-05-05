// WebSocket notifications for real-time BBS updates
(function() {
  const toastArea = document.getElementById('toast-area');
  if (!toastArea) return;

  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(proto + '//' + location.host + '/ws');

  ws.onmessage = function(e) {
    try {
      const data = JSON.parse(e.data);
      showToast(data.type, data.message);
      // Update unread badge
      const badge = document.querySelector('.nav-badge');
      if (badge && data.type === 'dm') {
        const current = parseInt(badge.textContent) || 0;
        badge.textContent = current + 1;
        badge.style.display = 'block';
      }
    } catch(err) {}
  };

  ws.onerror = function() {};
  ws.onclose = function() {};

  function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = '> ' + message;
    toastArea.appendChild(toast);
    setTimeout(function() {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s';
      setTimeout(function() { toast.remove(); }, 300);
    }, 5000);
  }

  window.showToast = showToast;
})();
