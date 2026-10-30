/* ============================================================
   FoodWise - shared front-end behaviour
   ============================================================ */

// Auto-dismiss flash messages after 6 seconds
window.setTimeout(function () {
  document.querySelectorAll('.alert-dismissible').forEach(function (el) {
    var alert = bootstrap.Alert.getOrCreateInstance(el);
    alert.close();
  });
}, 6000);

// Confirmation dialogs for destructive forms (declared via data-confirm)
document.addEventListener('submit', function (event) {
  var form = event.target;
  if (form.matches('[data-confirm]') && !window.confirm(form.dataset.confirm)) {
    event.preventDefault();
  }
}, true);

// Default purchase date = today on the add-item form
var purchaseInput = document.getElementById('purchase_date');
if (purchaseInput && !purchaseInput.value) {
  var now = new Date();
  var iso = now.getFullYear() + '-' +
    String(now.getMonth() + 1).padStart(2, '0') + '-' +
    String(now.getDate()).padStart(2, '0');
  purchaseInput.value = iso;
}

// Chart.js global defaults
if (window.Chart) {
  Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
  Chart.defaults.color = '#5f6b5f';
}

// Shared palette: greens first, then orange/red accents
window.APP_PALETTE = ['#2e7d32', '#66bb6a', '#f39c12', '#e67e22', '#c0392b', '#8d6e63'];

// Doughnut helper used by the dashboard
window.renderCategoryDoughnut = function (canvas, data) {
  if (!canvas || !window.Chart) return;
  var labels = Object.keys(data || {});
  if (!labels.length) return;
  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{ data: Object.values(data), backgroundColor: APP_PALETTE, borderWidth: 2 }]
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } }
    }
  });
};
