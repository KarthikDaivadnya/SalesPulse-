// SalesPulse dashboard logic — reads SALES_DATA (injected via _data_inline.js)
// and renders KPIs, charts, and drill-down tables, all reactive to the filter bar.

const fmtINR = (n) => '\u20b9' + Math.round(n).toLocaleString('en-IN');
const fmtNum = (n) => Math.round(n).toLocaleString('en-IN');

let charts = {};
let activeRegionRowFilter = null; // set when a region table row is clicked

function uniqueSorted(arr) {
  return [...new Set(arr)].sort();
}

function populateFilters() {
  const regions = uniqueSorted(SALES_DATA.map(d => d.region));
  const categories = uniqueSorted(SALES_DATA.map(d => d.product_category));
  const channels = uniqueSorted(SALES_DATA.map(d => d.source));
  const months = uniqueSorted(SALES_DATA.map(d => d.order_month));

  const fill = (id, values) => {
    const sel = document.getElementById(id);
    values.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v; opt.textContent = v;
      sel.appendChild(opt);
    });
  };
  fill('regionFilter', regions);
  fill('categoryFilter', categories);
  fill('channelFilter', channels);
  fill('monthFilter', months);

  const maxDate = SALES_DATA.reduce((m, d) => d.order_date > m ? d.order_date : m, '0000-00-00');
  document.getElementById('dataAsOf').textContent = maxDate;
}

function getFilteredData() {
  const region = document.getElementById('regionFilter').value;
  const category = document.getElementById('categoryFilter').value;
  const channel = document.getElementById('channelFilter').value;
  const month = document.getElementById('monthFilter').value;

  return SALES_DATA.filter(d => {
    if (region !== 'all' && d.region !== region) return false;
    if (category !== 'all' && d.product_category !== category) return false;
    if (channel !== 'all' && d.source !== channel) return false;
    if (month !== 'all' && d.order_month !== month) return false;
    if (activeRegionRowFilter && d.region !== activeRegionRowFilter) return false;
    return true;
  });
}

function computeKPIs(data) {
  const totalRevenue = data.reduce((s, d) => s + d.revenue, 0);
  const numOrders = data.length;
  const avgOrderValue = numOrders ? totalRevenue / numOrders : 0;
  const uniqueCustomers = new Set(data.filter(d => d.source === 'Online').map(d => d.customer_id)).size;

  // Month-over-month delta based on the two most recent months present in the filtered set
  const byMonth = {};
  data.forEach(d => { byMonth[d.order_month] = (byMonth[d.order_month] || 0) + d.revenue; });
  const months = Object.keys(byMonth).sort();
  let delta = null;
  if (months.length >= 2) {
    const last = byMonth[months[months.length - 1]];
    const prev = byMonth[months[months.length - 2]];
    delta = prev ? ((last - prev) / prev) * 100 : null;
  }

  return { totalRevenue, numOrders, avgOrderValue, uniqueCustomers, delta };
}

function renderKPIs(kpis) {
  const deltaHtml = kpis.delta === null
    ? ''
    : `<div class="kpi-delta ${kpis.delta >= 0 ? 'up' : 'down'}">${kpis.delta >= 0 ? '▲' : '▼'} ${Math.abs(kpis.delta).toFixed(1)}% last month</div>`;

  const cards = [
    { label: 'Total Revenue', value: fmtINR(kpis.totalRevenue), delta: deltaHtml },
    { label: 'Orders', value: fmtNum(kpis.numOrders), delta: '' },
    { label: 'Avg. Order Value', value: fmtINR(kpis.avgOrderValue), delta: '' },
    { label: 'Online Customers', value: fmtNum(kpis.uniqueCustomers), delta: '' },
  ];

  document.getElementById('kpiRow').innerHTML = cards.map(c => `
    <div class="kpi-card">
      <div class="kpi-label">${c.label}</div>
      <div class="kpi-value tabular">${c.value}</div>
      ${c.delta}
    </div>
  `).join('');
}

function renderTrendChart(data) {
  const byMonth = {};
  data.forEach(d => { byMonth[d.order_month] = (byMonth[d.order_month] || 0) + d.revenue; });
  const months = Object.keys(byMonth).sort();
  const values = months.map(m => byMonth[m]);

  if (charts.trend) charts.trend.destroy();
  const ctx = document.getElementById('trendChart');
  if (months.length === 0) { ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height); return; }

  charts.trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels: months,
      datasets: [{
        data: values,
        borderColor: '#5B86D6',
        backgroundColor: 'rgba(91,134,214,0.12)',
        fill: true,
        tension: 0.35,
        pointRadius: 3,
        pointBackgroundColor: '#5B86D6',
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => fmtINR(c.parsed.y) } } },
      scales: {
        x: { ticks: { color: '#8B96A8', font: { size: 11 } }, grid: { color: '#2A313D' } },
        y: { ticks: { color: '#8B96A8', font: { size: 11 }, callback: (v) => '\u20b9' + (v / 1000) + 'k' }, grid: { color: '#2A313D' } },
      }
    }
  });
}

function renderChannelChart(data) {
  const byChannel = {};
  data.forEach(d => { byChannel[d.source] = (byChannel[d.source] || 0) + d.revenue; });
  const labels = Object.keys(byChannel);
  const values = labels.map(l => byChannel[l]);

  if (charts.channel) charts.channel.destroy();
  const ctx = document.getElementById('channelChart');
  if (labels.length === 0) { ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height); return; }

  charts.channel = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: ['#2E5FAC', '#E8A33D'], borderColor: '#171C24', borderWidth: 3 }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#EDEFF2', font: { size: 12 }, padding: 14 } },
        tooltip: { callbacks: { label: (c) => `${c.label}: ${fmtINR(c.parsed)}` } }
      }
    }
  });
}

function renderRegionTable(data) {
  const byRegion = {};
  data.forEach(d => { byRegion[d.region] = (byRegion[d.region] || 0) + d.revenue; });
  const total = Object.values(byRegion).reduce((a, b) => a + b, 0);
  const rows = Object.entries(byRegion).sort((a, b) => b[1] - a[1]);
  const maxVal = rows.length ? rows[0][1] : 1;

  const tbody = document.querySelector('#regionTable tbody');
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" class="empty-state">No transactions match the current filters</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(([region, rev]) => `
    <tr style="cursor:pointer" onclick="setRegionDrilldown('${region}')" tabindex="0">
      <td>${region}</td>
      <td class="num tabular">${fmtINR(rev)}</td>
      <td class="num">
        <div class="bar-cell">
          <div class="bar-track"><div class="bar-fill" style="width:${(rev / maxVal * 100).toFixed(0)}%"></div></div>
          <span class="tabular" style="min-width:38px">${total ? (rev / total * 100).toFixed(0) : 0}%</span>
        </div>
      </td>
    </tr>
  `).join('');
}

function renderProductTable(data) {
  const byProduct = {};
  data.forEach(d => {
    if (!byProduct[d.product_name]) byProduct[d.product_name] = { units: 0, revenue: 0 };
    byProduct[d.product_name].units += d.quantity;
    byProduct[d.product_name].revenue += d.revenue;
  });
  const rows = Object.entries(byProduct).sort((a, b) => b[1].revenue - a[1].revenue).slice(0, 6);

  const tbody = document.querySelector('#productTable tbody');
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" class="empty-state">No transactions match the current filters</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(([name, v]) => `
    <tr><td>${name}</td><td class="num tabular">${fmtNum(v.units)}</td><td class="num tabular">${fmtINR(v.revenue)}</td></tr>
  `).join('');
}

function renderCategoryTable(data) {
  const byCategory = {};
  data.forEach(d => {
    if (!byCategory[d.product_category]) byCategory[d.product_category] = { txns: 0, units: 0, revenue: 0 };
    byCategory[d.product_category].txns += 1;
    byCategory[d.product_category].units += d.quantity;
    byCategory[d.product_category].revenue += d.revenue;
  });
  const rows = Object.entries(byCategory).sort((a, b) => b[1].revenue - a[1].revenue);

  const tbody = document.querySelector('#categoryTable tbody');
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No transactions match the current filters</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(([cat, v]) => `
    <tr>
      <td>${cat}</td>
      <td class="num tabular">${fmtNum(v.txns)}</td>
      <td class="num tabular">${fmtNum(v.units)}</td>
      <td class="num tabular">${fmtINR(v.revenue)}</td>
      <td class="num tabular">${fmtINR(v.revenue / v.txns)}</td>
    </tr>
  `).join('');
}

function safeRender(label, fn) {
  try {
    fn();
  } catch (err) {
    console.error(`SalesPulse: ${label} failed to render`, err);
  }
}

function renderAll() {
  const data = getFilteredData();
  safeRender('KPIs', () => renderKPIs(computeKPIs(data)));
  safeRender('trend chart', () => renderTrendChart(data));
  safeRender('channel chart', () => renderChannelChart(data));
  safeRender('region table', () => renderRegionTable(data));
  safeRender('product table', () => renderProductTable(data));
  safeRender('category table', () => renderCategoryTable(data));
}

function setRegionDrilldown(region) {
  activeRegionRowFilter = (activeRegionRowFilter === region) ? null : region;
  renderAll();
}

function resetFilters() {
  ['regionFilter', 'categoryFilter', 'channelFilter', 'monthFilter'].forEach(id => {
    document.getElementById(id).value = 'all';
  });
  activeRegionRowFilter = null;
  renderAll();
}

document.addEventListener('DOMContentLoaded', () => {
  populateFilters();
  ['regionFilter', 'categoryFilter', 'channelFilter', 'monthFilter'].forEach(id => {
    document.getElementById(id).addEventListener('change', renderAll);
  });
  document.getElementById('resetBtn').addEventListener('click', resetFilters);
  renderAll();
});
