// Renders the staff analytics dashboard charts from server-provided data.
// Data is injected via Django's json_script tag (#chart-data); Chart.js is
// loaded from CDN just before this file.
(function () {
    'use strict';

    var dataEl = document.getElementById('chart-data');
    if (!dataEl || typeof Chart === 'undefined') {
        return;
    }
    var data = JSON.parse(dataEl.textContent);
    var COLOR = '#4e73df';
    var COLOR_ALT = '#1cc88a';

    function makeBar(canvasId, labels, datasets, horizontal) {
        var canvas = document.getElementById(canvasId);
        if (!canvas || !labels.length) {
            return;
        }
        new Chart(canvas, {
            type: 'bar',
            data: { labels: labels, datasets: datasets },
            options: {
                indexAxis: horizontal ? 'y' : 'x',
                responsive: true,
                plugins: { legend: { display: datasets.length > 1 } },
                scales: { x: { beginAtZero: true }, y: { beginAtZero: true } }
            }
        });
    }

    // Funnel
    makeBar('funnelChart', data.funnel.labels, [{
        label: 'Count', data: data.funnel.counts, backgroundColor: COLOR
    }], true);

    // Activity over time (line)
    var tsCanvas = document.getElementById('timeseriesChart');
    if (tsCanvas && data.timeseries.labels.length) {
        new Chart(tsCanvas, {
            type: 'line',
            data: {
                labels: data.timeseries.labels,
                datasets: [{
                    label: 'Events', data: data.timeseries.counts,
                    borderColor: COLOR, backgroundColor: 'rgba(78,115,223,0.1)',
                    fill: true, tension: 0.3
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    // Story impact (grouped bars)
    makeBar('storyChart', data.story.labels, [
        { label: 'Avg views / farmer', data: data.story.avg_views, backgroundColor: COLOR },
        { label: 'Avg active / farmer', data: data.story.avg_active, backgroundColor: COLOR_ALT }
    ], false);

    // Active connections by farmer country
    makeBar('farmerCountryChart', data.farmer_country.labels, [{
        label: 'Active', data: data.farmer_country.counts, backgroundColor: COLOR_ALT
    }], true);
})();
