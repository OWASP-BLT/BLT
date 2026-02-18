/**
 * Security Dashboard - Chart initialization and tab switching.
 * Requires ApexCharts to be loaded before this script.
 */

var _activityChartsInitialized = false;
var _dashboardConfig = null;

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

    // Lazy-init activity charts on first switch to avoid rendering in hidden tab
    if (tabName === "activity" && !_activityChartsInitialized && _dashboardConfig) {
        _activityChartsInitialized = true;
        initLoginPieChart(_dashboardConfig.loginSuccessCount, _dashboardConfig.loginFailedCount);
        initHourlyChart(_dashboardConfig.hourlyLoginData);
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
    var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (!csrfToken) {
        // Fallback: read from cookie
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.indexOf("csrftoken=") === 0) {
                csrfToken = c.substring("csrftoken=".length);
                break;
            }
        }
    } else {
        csrfToken = csrfToken.value;
    }

    var formData = new FormData();
    formData.append("action", "dismiss_anomaly");
    formData.append("id", anomalyId);

    fetch("/security/api/user-activity/", {
        method: "POST",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrfToken,
        },
        credentials: "same-origin",
        body: formData,
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
    _dashboardConfig = config;
    initSeverityChart(config.severityData);
    // Activity charts are lazy-initialized on first tab switch
}
