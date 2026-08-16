// Time display
function updateTime() {
    const el = document.getElementById('timeDisplay');
    if (el) el.textContent = new Date().toLocaleTimeString('en-US', {hour12: false});
}
updateTime();
setInterval(updateTime, 1000);

// Toast
function showToast(msg, type='success') {
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

// Auto-dismiss top flash alerts
setTimeout(() => {
    document.querySelectorAll('.alerts-container .alert').forEach(a => {
        a.style.transition = 'opacity 0.5s';
        a.style.opacity = '0';
        setTimeout(() => a.remove(), 500);
    });
}, 5000);

// Jinja2 enumerate helper workaround - already handled server-side
