/**
 * Security Dashboard - Chart initialization and tab switching.
 * Requires ApexCharts to be loaded before this script.
 */

function switchTab(tabName) {
    var panels = document.querySelectorAll("[data-panel]");
    var tabs = document.querySelectorAll("[data-tab]");
    var i;

    for (i = 0; i < panels.length; i++) {
        panels[i].classList.add("hidden");
    }
    for (i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove("border-red-500", "text-red-600");
        tabs[i].classList.add("border-transparent", "text-gray-500");
    }

    var activePanel = document.querySelector('[data-panel="' + tabName + '"]');
    var activeTab = document.querySelector('[data-tab="' + tabName + '"]');

    if (activePanel) {
        activePanel.classList.remove("hidden");
    }
    if (activeTab) {
        activeTab.classList.remove("border-transparent", "text-gray-500");
        activeTab.classList.add("border-red-500", "text-red-600");
    }
}

function initSeverityChart(data) {
    var el = document.getElementById("severity-chart");
    if (!el || typeof ApexCharts === "undefined" || data.length === 0) {
        return;
    }

    var labels = data.map(function (item) {
        return item.severity.charAt(0).toUpperCase() + item.severity.slice(1);
    });
    var series = data.map(function (item) {
        return item.total;
    });

    var chart = new ApexCharts(el, {
        chart: { type: "donut", height: 200 },
        labels: labels,
        series: series,
        legend: { position: "bottom" },
        dataLabels: { enabled: false },
        stroke: { show: false },
    });
    chart.render();
}

function initLoginPieChart(successCount, failedCount) {
    var el = document.getElementById("login-pie-chart");
    if (!el || typeof ApexCharts === "undefined") {
        return;
    }
    if (successCount === 0 && failedCount === 0) {
        return;
    }

    var chart = new ApexCharts(el, {
        chart: { type: "donut", height: 220 },
        labels: ["Successful", "Failed"],
        series: [successCount, failedCount],
        colors: ["#22c55e", "#e74c3c"],
        legend: { position: "bottom" },
        dataLabels: { enabled: false },
        stroke: { show: false },
    });
    chart.render();
}

function initHourlyChart(hourlyData) {
    var el = document.getElementById("hourly-login-chart");
    if (!el || typeof ApexCharts === "undefined") {
        return;
    }

    var hours = [];
    var counts = [];
    var i;

    for (i = 0; i < 24; i++) {
        hours.push(i + ":00");
        counts.push(0);
    }

    for (i = 0; i < hourlyData.length; i++) {
        counts[hourlyData[i].hour] = hourlyData[i].count;
    }

    var chart = new ApexCharts(el, {
        chart: { type: "bar", height: 220 },
        series: [{ name: "Logins", data: counts }],
        xaxis: { categories: hours },
        colors: ["#e74c3c"],
        dataLabels: { enabled: false },
        plotOptions: { bar: { borderRadius: 2 } },
    });
    chart.render();
}

function dismissAnomaly(anomalyId, buttonEl) {
    var url = "/security/api/user-activity/?action=dismiss_anomaly&id=" + anomalyId;

    fetch(url, {
        method: "GET",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
    })
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            if (data.status === "dismissed") {
                var row = buttonEl.closest("tr");
                if (row) {
                    row.remove();
                }
                var badge = document.getElementById("anomaly-count-badge");
                if (badge) {
                    var current = parseInt(badge.textContent, 10);
                    if (current > 1) {
                        badge.textContent = current - 1;
                    } else {
                        badge.textContent = "0";
                    }
                }
            }
        });
}

function initSecurityDashboard(config) {
    initSeverityChart(config.severityData);
    initLoginPieChart(config.loginSuccessCount, config.loginFailedCount);
    initHourlyChart(config.hourlyLoginData);
}
