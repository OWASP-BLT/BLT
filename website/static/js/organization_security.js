/* Cybersecurity neon color palette for dashboard charts */
var CYBER = {
    cyan: "#00FFFF",
    green: "#00FF88",
    red: "#FF3366",
    amber: "#FFD700",
    blue: "#0080FF",
    purple: "#A855F7",
    orange: "#FF8C00",
    grid: "rgba(0, 255, 255, 0.06)",
    gridStrong: "rgba(0, 255, 255, 0.12)",
    axis: "#475569",
    text: "#94A3B8",
    textMuted: "#64748B",
    bg: "#0D1321",
    bgDeep: "#0A0E1A",
    border: "rgba(0, 255, 255, 0.15)",
    critical: "#FF3366",
    high: "#FF8C00",
    medium: "#FFD700",
    low: "#0080FF",
    open: "#FF3366",
    investigating: "#FFD700",
    resolved: "#00FF88",
    successBg: "rgba(0, 255, 136, 0.15)",
    failBg: "rgba(255, 51, 102, 0.15)",
    cyanBg: "rgba(0, 255, 255, 0.1)",
    purpleBg: "rgba(168, 85, 247, 0.15)",
    blueBg: "rgba(0, 128, 255, 0.15)",
    amberBg: "rgba(255, 215, 0, 0.15)",
};

/* Shared tooltip configuration for consistent neon styling */
var cyberTooltip = {
    backgroundColor: "#0D1321",
    titleColor: "#E2E8F0",
    bodyColor: "#94A3B8",
    borderColor: "rgba(0,255,255,0.2)",
    borderWidth: 1,
};

document.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined") {
        return;
    }

    var config = window.ORG_SECURITY_CONFIG;
    if (!config) return;

    Chart.defaults.color = CYBER.text;
    Chart.defaults.font.family = "ui-monospace, 'Cascadia Code', 'Fira Code', monospace";
    Chart.defaults.font.size = 10;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.pointStyleWidth = 8;

    initRiskGauge(config.riskScore);
    initSeverityChart(config.severityLabels, config.severityCounts);
    initHourlyChart(config.hourlyData);
    initDailyTrendChart(config.dailyLoginLabels, config.dailyLoginCounts);
    initLoginTypeChart(config.loginTypeLabels, config.loginTypeCounts);
    initAnomalyTypeChart(config.anomalyTypeLabels, config.anomalyTypeCounts);
    initDailyFailedChart(config.dailyFailedLabels, config.dailyFailedCounts);
    initResolutionGauge(config.anomalyResolutionRate);

    initMonthlyIncidentChart(
        config.monthlyIncidentLabels,
        config.monthlyIncidentTotals,
        config.monthlyIncidentCriticals,
    );
    initAffectedSystemsChart(config.affectedSystemsLabels, config.affectedSystemsCounts);
    initThreatTypeChart(config.threatTypeLabels, config.threatTypeCounts);
    initThreatSeverityChart(config.threatSevCounts);
    initIpDiversityChart(config.ipDiversityLabels, config.ipDiversityCounts);
    initDailyTrafficChart(config.dailyTrafficLabels, config.dailyTrafficCounts);
    initVulnSeverityChart(config.vulnSeverityLabels, config.vulnSeverityCounts);
    initVulnStatusChart(config.vulnStatusLabels, config.vulnStatusCounts);
    initComplianceGauge(config.overallCompliancePct);
    initRadarMinimap();
    initWorldMap(config.mapMarkers || [], config.topCountries || []);
});

/* ── Gauge Charts ── */

function initRiskGauge(riskScore) {
    var ctx = document.getElementById("riskGaugeChart");
    if (!ctx) return;

    var score = Math.max(0, Math.min(100, riskScore || 0));
    var color = score >= 70 ? CYBER.red : score >= 40 ? CYBER.amber : CYBER.green;

    new Chart(ctx, {
        type: "doughnut",
        data: {
            datasets: [
                {
                    data: [score, 100 - score],
                    backgroundColor: [color, "rgba(0,255,255,0.08)"],
                    borderWidth: 0,
                },
            ],
        },
        options: {
            cutout: "75%",
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
        },
    });
}

function initResolutionGauge(rate) {
    var ctx = document.getElementById("resolutionGaugeChart");
    if (!ctx) return;

    var val = Math.max(0, Math.min(100, rate || 0));
    var color = val >= 70 ? CYBER.green : val >= 40 ? CYBER.amber : CYBER.red;

    new Chart(ctx, {
        type: "doughnut",
        data: {
            datasets: [
                {
                    data: [val, 100 - val],
                    backgroundColor: [color, "rgba(0,255,255,0.08)"],
                    borderWidth: 0,
                },
            ],
        },
        options: {
            cutout: "75%",
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
        },
    });
}

/* ── Bar / Line Charts ── */

function initSeverityChart(labels, counts) {
    var ctx = document.getElementById("severityChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    var colors = [CYBER.critical, CYBER.high, CYBER.medium, CYBER.low];

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: colors,
                    borderColor: colors,
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: 14,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { display: false },
                },
            },
        },
    });
}

function initHourlyChart(hourlyData) {
    var ctx = document.getElementById("hourlyChart");
    if (!ctx) return;
    if (!Array.isArray(hourlyData)) return;

    var hours = [];
    var counts = [];
    for (var h = 0; h < 24; h++) {
        hours.push(h + ":00");
        counts.push(0);
    }
    for (var i = 0; i < hourlyData.length; i++) {
        var entry = hourlyData[i];
        if (entry && typeof entry.hour === "number" && entry.hour >= 0 && entry.hour < 24) {
            counts[entry.hour] = entry.count || 0;
        }
    }

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: hours,
            datasets: [
                {
                    data: counts,
                    backgroundColor: CYBER.blue,
                    borderColor: CYBER.blue,
                    borderWidth: 1,
                    hoverBackgroundColor: CYBER.cyan,
                    borderRadius: 2,
                    barThickness: 5,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    ticks: {
                        color: CYBER.textMuted,
                        maxRotation: 0,
                        font: { size: 8 },
                        callback: function (val, index) {
                            return index % 6 === 0 ? this.getLabelForValue(val) : "";
                        },
                    },
                    grid: { color: CYBER.grid },
                },
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 8 } },
                    grid: { color: CYBER.grid },
                },
            },
        },
    });
}

function initDailyTrendChart(labels, counts) {
    var ctx = document.getElementById("dailyTrendChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    borderColor: CYBER.cyan,
                    backgroundColor: CYBER.cyanBg,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: CYBER.cyan,
                    fill: true,
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
            },
        },
    });
}

function initDailyFailedChart(labels, counts) {
    var ctx = document.getElementById("dailyFailedChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    borderColor: CYBER.red,
                    backgroundColor: CYBER.failBg,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: CYBER.red,
                    fill: true,
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
            },
        },
    });
}

function initLoginTypeChart(labels, counts) {
    var ctx = document.getElementById("loginTypeChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: [CYBER.green, CYBER.textMuted, CYBER.red],
                    borderColor: CYBER.bg,
                    borderWidth: 1,
                },
            ],
        },
        options: {
            cutout: "65%",
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: Object.assign({}, cyberTooltip, {
                    callbacks: {
                        label: function (context) {
                            return context.label + ": " + context.parsed;
                        },
                    },
                }),
            },
        },
    });
}

function initAnomalyTypeChart(labels, counts) {
    var ctx = document.getElementById("anomalyTypeChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    var colors = [CYBER.cyan, CYBER.purple, CYBER.amber, CYBER.red];

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: colors,
                    borderColor: colors,
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: 14,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    ticks: { color: CYBER.textMuted, font: { size: 8 }, maxRotation: 0 },
                    grid: { color: CYBER.grid },
                },
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 8 } },
                    grid: { color: CYBER.grid },
                },
            },
        },
    });
}

/* ── Dashboard Component Charts ── */

function initMonthlyIncidentChart(labels, totalCounts, criticalCounts) {
    var ctx = document.getElementById("monthlyIncidentChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(totalCounts)) return;

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Total",
                    data: totalCounts,
                    backgroundColor: CYBER.blueBg,
                    borderColor: CYBER.blue,
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: 14,
                },
                {
                    label: "Critical",
                    data: criticalCounts || [],
                    backgroundColor: CYBER.red,
                    borderColor: CYBER.red,
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: 14,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: "top",
                    labels: {
                        color: CYBER.text,
                        font: { size: 9 },
                        boxWidth: 10,
                        padding: 8,
                    },
                },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
            },
        },
    });
}

function initAffectedSystemsChart(labels, counts) {
    var ctx = document.getElementById("affectedSystemsChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: CYBER.purple,
                    borderColor: CYBER.purple,
                    borderWidth: 1,
                    hoverBackgroundColor: CYBER.cyan,
                    borderRadius: 4,
                    barThickness: 14,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { display: false },
                },
            },
        },
    });
}

function initThreatTypeChart(labels, counts) {
    var ctx = document.getElementById("threatTypeChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    var colors = [CYBER.red, CYBER.orange, CYBER.amber, CYBER.purple, CYBER.blue];
    var slicedColors = colors.slice(0, labels.length);
    /* Cycle colors for labels exceeding the palette length */
    while (slicedColors.length < labels.length) {
        slicedColors.push(colors[slicedColors.length % colors.length]);
    }

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: slicedColors,
                    borderColor: slicedColors,
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: 14,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { display: false },
                },
            },
        },
    });
}

function initThreatSeverityChart(counts) {
    var ctx = document.getElementById("threatSeverityChart");
    if (!ctx) return;
    if (!Array.isArray(counts)) return;

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Critical", "High", "Medium", "Low"],
            datasets: [
                {
                    data: counts,
                    backgroundColor: [CYBER.critical, CYBER.high, CYBER.medium, CYBER.low],
                    borderColor: CYBER.bg,
                    borderWidth: 1,
                },
            ],
        },
        options: {
            cutout: "65%",
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: Object.assign({}, cyberTooltip, {
                    callbacks: {
                        label: function (context) {
                            return context.label + ": " + context.parsed;
                        },
                    },
                }),
            },
        },
    });
}

function initIpDiversityChart(labels, counts) {
    var ctx = document.getElementById("ipDiversityChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    borderColor: CYBER.cyan,
                    backgroundColor: CYBER.cyanBg,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: CYBER.cyan,
                    fill: true,
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
            },
        },
    });
}

function initDailyTrafficChart(labels, counts) {
    var ctx = document.getElementById("dailyTrafficChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    borderColor: CYBER.green,
                    backgroundColor: CYBER.successBg,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: CYBER.green,
                    hoverPointBackgroundColor: CYBER.cyan,
                    fill: true,
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
            },
        },
    });
}

function initVulnSeverityChart(labels, counts) {
    var ctx = document.getElementById("vulnSeverityChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    var colorMap = {
        Critical: CYBER.critical,
        High: CYBER.high,
        Medium: CYBER.medium,
        Low: CYBER.low,
    };
    var colors = labels.map(function (l) {
        return colorMap[l] || CYBER.textMuted;
    });

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: colors,
                    borderColor: colors,
                    borderWidth: 1,
                    borderRadius: 4,
                    barThickness: 14,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
                tooltip: cyberTooltip,
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted, font: { size: 9 } },
                    grid: { color: CYBER.grid },
                },
                y: {
                    ticks: { color: CYBER.textMuted, font: { size: 9 } },
                    grid: { display: false },
                },
            },
        },
    });
}

function initVulnStatusChart(labels, counts) {
    var ctx = document.getElementById("vulnStatusChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    var colorMap = {
        Open: CYBER.red,
        "In Progress": CYBER.amber,
        Remediated: CYBER.green,
        "Accepted Risk": CYBER.purple,
        "False Positive": CYBER.textMuted,
    };
    var colors = labels.map(function (l) {
        return colorMap[l] || CYBER.textMuted;
    });

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: colors,
                    borderColor: CYBER.bg,
                    borderWidth: 1,
                },
            ],
        },
        options: {
            cutout: "65%",
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: Object.assign({}, cyberTooltip, {
                    callbacks: {
                        label: function (context) {
                            return context.label + ": " + context.parsed;
                        },
                    },
                }),
            },
        },
    });
}

function initComplianceGauge(pct) {
    var ctx = document.getElementById("complianceGaugeChart");
    if (!ctx) return;

    var val = Math.max(0, Math.min(100, pct || 0));
    var color = val >= 80 ? CYBER.green : val >= 50 ? CYBER.amber : CYBER.red;

    new Chart(ctx, {
        type: "doughnut",
        data: {
            datasets: [
                {
                    data: [val, 100 - val],
                    backgroundColor: [color, "rgba(0,255,255,0.08)"],
                    borderWidth: 0,
                },
            ],
        },
        options: {
            cutout: "75%",
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
        },
    });
}

/* ── Radar Minimap ── */

function initRadarMinimap() {
    var container = document.getElementById("radar-dots");
    if (!container) return;

    var config = window.ORG_SECURITY_CONFIG;
    var subnets = config.minimapSubnets || [];
    if (!subnets.length) return;

    var maxTotal = Math.max.apply(
        null,
        subnets.map(function (s) {
            return s.total;
        }),
    );
    var cx = 90,
        cy = 90;
    var radius = 65;

    subnets.forEach(function (subnet, i) {
        var angle = (i / subnets.length) * 2 * Math.PI - Math.PI / 2;
        var x = cx + radius * Math.cos(angle);
        var y = cy + radius * Math.sin(angle);
        var size = Math.max(6, Math.min(16, (subnet.total / maxTotal) * 16));
        var failRatio = subnet.total > 0 ? subnet.failed / subnet.total : 0;
        var color = failRatio > 0.5 ? "#FF3366" : failRatio > 0.2 ? "#FFD700" : "#00FF88";

        var dot = document.createElement("div");
        dot.className = "radar-dot";
        dot.style.width = size + "px";
        dot.style.height = size + "px";
        dot.style.backgroundColor = color;
        dot.style.boxShadow = "0 0 " + size / 2 + "px " + color;
        dot.style.left = x - size / 2 + "px";
        dot.style.top = y - size / 2 + "px";
        dot.title =
            subnet.subnet + " (" + subnet.total + " events, " + subnet.failed + " failed)";
        container.appendChild(dot);
    });
}

/* ── World Map (Leaflet) ── */

function initWorldMap(markers, topCountries) {
    var mapEl = document.getElementById("world-map");
    if (!mapEl || typeof L === "undefined") return;

    var map = L.map("world-map", {
        center: [20, 0],
        zoom: 2,
        minZoom: 2,
        maxZoom: 10,
        zoomControl: true,
        attributionControl: false,
        scrollWheelZoom: true,
        worldCopyJump: true,
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        subdomains: "abcd",
        maxZoom: 20,
    }).addTo(map);

    if (markers.length > 0 && L.heatLayer) {
        var heatData = markers.map(function (m) {
            return [m.lat, m.lng, m.total];
        });
        L.heatLayer(heatData, {
            radius: 25,
            blur: 20,
            maxZoom: 8,
            gradient: {
                0.2: "#0080FF",
                0.4: "#00FF88",
                0.6: "#FFD700",
                0.8: "#FF3366",
                1.0: "#FF0040",
            },
        }).addTo(map);
    }

    markers.forEach(function (m) {
        var isFailed = m.failed > m.total * 0.3;
        var color = isFailed ? "#FF3366" : "#00FF88";
        var size = Math.max(6, Math.min(20, m.total * 2));
        var half = size / 2;

        var icon = L.divIcon({
            className: "",
            html:
                '<div style="position:relative;width:' +
                size +
                "px;height:" +
                size +
                'px">' +
                '<div style="position:absolute;inset:0;border-radius:50%;background:' +
                color +
                ';opacity:0.3;animation:map-ping 2s cubic-bezier(0,0,0.2,1) infinite"></div>' +
                '<div style="width:' +
                size +
                "px;height:" +
                size +
                "px;border-radius:50%;background:" +
                color +
                ';border:1px solid rgba(255,255,255,0.3)"></div>' +
                "</div>",
            iconSize: [size, size],
            iconAnchor: [half, half],
        });

        var popupHtml =
            '<div style="font-family:ui-monospace,monospace;font-size:11px;color:#E2E8F0;' +
            "background:#0D1321;padding:8px;border:1px solid rgba(0,255,255,0.3);" +
            'border-radius:6px;min-width:160px">' +
            '<div style="font-weight:700;color:#00FFFF;margin-bottom:4px">' +
            escapeHtml(m.city || "Unknown") +
            ", " +
            escapeHtml(m.country || "Unknown") +
            "</div>" +
            "<div>ISP: " +
            escapeHtml(m.isp || "N/A") +
            "</div>" +
            '<div style="color:#00FF88">Logins: ' +
            m.total +
            "</div>" +
            '<div style="color:#FF3366">Failed: ' +
            m.failed +
            "</div>" +
            "</div>";

        L.marker([m.lat, m.lng], { icon: icon })
            .addTo(map)
            .bindPopup(popupHtml, { className: "cyber-popup" });
    });

    var statsEl = document.getElementById("country-stats");
    if (statsEl && topCountries && topCountries.length > 0) {
        var maxCount = topCountries[0].total || 1;
        statsEl.innerHTML = topCountries
            .map(function (c) {
                var pct = Math.round((c.total / maxCount) * 100);
                var failPct = c.total > 0 ? Math.round((c.failed / c.total) * 100) : 0;
                var barColor = failPct > 30 ? "#FF3366" : "#00FF88";
                return (
                    '<div class="flex flex-col gap-0.5">' +
                    '<div class="flex justify-between">' +
                    '<span class="text-[#E2E8F0] cyber-mono">' +
                    escapeHtml(c.country) +
                    "</span>" +
                    '<span class="text-[#00FFFF] cyber-mono">' +
                    c.total +
                    "</span>" +
                    "</div>" +
                    '<div class="h-1 bg-[rgba(0,255,255,0.1)] rounded overflow-hidden">' +
                    '<div class="h-full rounded" style="width:' +
                    pct +
                    "%;background:linear-gradient(90deg,#0080FF," +
                    barColor +
                    ')"></div>' +
                    "</div>" +
                    "</div>"
                );
            })
            .join("");
    }

    var uniqueCountries = {};
    var totalFailed = 0;
    markers.forEach(function (m) {
        if (m.country) uniqueCountries[m.country] = true;
        totalFailed += m.failed;
    });

    var locEl = document.getElementById("map-total-locations");
    var countryEl = document.getElementById("map-total-countries");
    var failedEl = document.getElementById("map-total-failed");
    if (locEl) locEl.textContent = markers.length;
    if (countryEl) countryEl.textContent = Object.keys(uniqueCountries).length;
    if (failedEl) failedEl.textContent = totalFailed;
}

/* ── Expand / Collapse KPI Panels ── */

function toggleExpand(cardId) {
    var panel = document.getElementById("expand-" + cardId);
    var chevron = document.getElementById("chevron-" + cardId);
    if (!panel) return;

    var isHidden = panel.classList.contains("hidden");

    if (isHidden) {
        panel.classList.remove("transition-all", "duration-300");

        panel.classList.remove("hidden", "overflow-hidden");
        panel.style.maxHeight = "none";
        var targetHeight = panel.scrollHeight;

        panel.classList.add("overflow-hidden");
        panel.style.maxHeight = "0px";
        void panel.offsetHeight;

        panel.classList.add("transition-all", "duration-300");
        void panel.offsetHeight;

        if (cardId === "logins" || cardId === "failed" || cardId === "anomalies-card") {
            loadExpandContent(cardId);
        }
        setTimeout(function () {
            panel.style.maxHeight = targetHeight + "px";
        }, 10);
        if (chevron) chevron.style.transform = "rotate(180deg)";
    } else {
        panel.style.maxHeight = panel.scrollHeight + "px";
        void panel.offsetHeight;
        panel.style.maxHeight = "0px";
        if (chevron) chevron.style.transform = "";
        setTimeout(function () {
            panel.classList.add("hidden");
        }, 300);
    }
}

function loadExpandContent(cardId) {
    var config = window.ORG_SECURITY_CONFIG;
    if (!config) return;

    var contentEl = document.getElementById("expand-" + cardId + "-content");
    if (!contentEl) return;

    var action = "";
    var title = "";
    if (cardId === "logins") {
        action = "events";
        title = "Recent Login Events";
    } else if (cardId === "failed") {
        action = "events";
        title = "Recent Failed Logins";
    } else if (cardId === "anomalies-card") {
        action = "anomalies";
        title = "Active Anomalies";
    }

    contentEl.innerHTML =
        '<p class="text-xs text-gray-400"><i class="fas fa-spinner fa-spin mr-1"></i>Loading...</p>';

    var url = "/organization/" + config.orgId + "/api/security/?action=" + action;

    fetch(url, { credentials: "same-origin" })
        .then(function (r) {
            if (!r.ok) throw new Error("Request failed with status " + r.status);
            return r.json();
        })
        .then(function (data) {
            if (action === "events" && data.events) {
                var rows = data.events;
                if (cardId === "failed") {
                    rows = rows.filter(function (e) {
                        return (
                            e.event_type &&
                            e.event_type.toLowerCase().indexOf("fail") !== -1
                        );
                    });
                }
                contentEl.innerHTML = buildEventsTable(title, rows);
            } else if (action === "anomalies" && data.anomalies) {
                contentEl.innerHTML = buildAnomaliesTable(title, data.anomalies);
            } else {
                contentEl.innerHTML = '<p class="text-xs text-gray-400">No data available</p>';
            }
            var panel = document.getElementById("expand-" + cardId);
            if (panel) {
                panel.style.maxHeight = panel.scrollHeight + "px";
            }
        })
        .catch(function () {
            contentEl.innerHTML = '<p class="text-xs text-red-400">Failed to load data</p>';
        });
}

function buildEventsTable(title, events) {
    var html = '<h4 class="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">' + escapeHtml(title) + "</h4>";
    html += '<table class="w-full text-xs">';
    html +=
        "<thead><tr class=\"border-b border-gray-200 dark:border-gray-700\">" +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">User</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Type</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">IP</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Time</th>' +
        "</tr></thead><tbody>";
    if (events.length === 0) {
        html +=
            '<tr><td colspan="4" class="py-4 text-center text-gray-400">No events found</td></tr>';
    }
    for (var i = 0; i < events.length; i++) {
        var e = events[i];
        var typeBadge = getTypeBadge(e.event_type);
        html +=
            '<tr class="border-b border-gray-50 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">' +
            '<td class="py-1.5 px-2 text-gray-900 dark:text-gray-100 font-medium">' +
            escapeHtml(e.username) +
            "</td>" +
            '<td class="py-1.5 px-2">' +
            typeBadge +
            "</td>" +
            '<td class="py-1.5 px-2 text-gray-500 font-mono text-[10px]">' +
            escapeHtml(e.ip_address || "-") +
            "</td>" +
            '<td class="py-1.5 px-2 text-gray-400 text-[10px]">' +
            formatTimestamp(e.timestamp) +
            "</td></tr>";
    }
    html += "</tbody></table>";
    return html;
}

function buildAnomaliesTable(title, anomalies) {
    var html = '<h4 class="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">' + escapeHtml(title) + "</h4>";
    html += '<table class="w-full text-xs">';
    html +=
        "<thead><tr class=\"border-b border-gray-200 dark:border-gray-700\">" +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">User</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Type</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Severity</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Description</th>' +
        "</tr></thead><tbody>";
    if (anomalies.length === 0) {
        html +=
            '<tr><td colspan="4" class="py-4 text-center text-gray-400">No anomalies found</td></tr>';
    }
    for (var i = 0; i < anomalies.length; i++) {
        var a = anomalies[i];
        html +=
            '<tr class="border-b border-gray-50 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">' +
            '<td class="py-1.5 px-2 text-gray-900 dark:text-gray-100 font-medium">' +
            escapeHtml(a.username) +
            "</td>" +
            '<td class="py-1.5 px-2 text-gray-600 dark:text-gray-300">' +
            escapeHtml(a.anomaly_type) +
            "</td>" +
            '<td class="py-1.5 px-2">' +
            getSeverityBadge(a.severity) +
            "</td>" +
            '<td class="py-1.5 px-2 text-gray-500 text-[10px] truncate max-w-[200px]">' +
            escapeHtml(a.description || "") +
            "</td></tr>";
    }
    html += "</tbody></table>";
    return html;
}

/* ── Chart Fullscreen Modal ── */

var chartModalInstance = null;

function openChartModal(chartId, title) {
    var modal = document.getElementById("chart-modal");
    var content = document.getElementById("chart-modal-content");
    var titleEl = document.getElementById("chart-modal-title");
    var canvas = document.getElementById("chart-modal-canvas");
    if (!modal || !content || !canvas) return;

    titleEl.textContent = title;

    if (chartModalInstance) {
        chartModalInstance.destroy();
        chartModalInstance = null;
    }

    var sourceCanvas = document.getElementById(chartId);
    if (!sourceCanvas) return;
    var sourceChart = Chart.getChart(sourceCanvas);
    if (!sourceChart) return;

    modal.classList.remove("hidden");
    modal.classList.add("flex");
    requestAnimationFrame(function () {
        content.classList.remove("scale-95", "opacity-0");
        content.classList.add("scale-100", "opacity-100");

        var chartType = sourceChart.config.type;
        var chartData = JSON.parse(JSON.stringify(sourceChart.data));
        var modalOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display:
                        sourceChart.config.options &&
                        sourceChart.config.options.plugins &&
                        sourceChart.config.options.plugins.legend
                            ? sourceChart.config.options.plugins.legend.display
                            : false,
                },
                tooltip: Object.assign({ enabled: true }, cyberTooltip),
            },
        };
        if (
            sourceChart.config.options &&
            sourceChart.config.options.indexAxis === "y"
        ) {
            modalOptions.indexAxis = "y";
        }
        if (chartType === "doughnut") {
            var cutout =
                sourceChart.config.options && sourceChart.config.options.cutout
                    ? sourceChart.config.options.cutout
                    : "65%";
            modalOptions.cutout = cutout;
        }
        if (chartType !== "doughnut") {
            modalOptions.scales = {
                x: {
                    ticks: { color: CYBER.textMuted },
                    grid: { color: CYBER.grid },
                },
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: CYBER.textMuted },
                    grid: { color: CYBER.grid },
                },
            };
        }

        chartModalInstance = new Chart(canvas, {
            type: chartType,
            data: chartData,
            options: modalOptions,
        });
    });
}

function closeChartModal() {
    var modal = document.getElementById("chart-modal");
    var content = document.getElementById("chart-modal-content");
    if (!modal || !content) return;

    content.classList.remove("scale-100", "opacity-100");
    content.classList.add("scale-95", "opacity-0");
    setTimeout(function () {
        modal.classList.remove("flex");
        modal.classList.add("hidden");
        if (chartModalInstance) {
            chartModalInstance.destroy();
            chartModalInstance = null;
        }
    }, 200);
}

/* ── Drill-down Modal ── */

function drillDown(action, params) {
    var config = window.ORG_SECURITY_CONFIG;
    if (!config) return;

    var modal = document.getElementById("drilldown-modal");
    var content = document.getElementById("drilldown-modal-content");
    var titleEl = document.getElementById("drilldown-modal-title");
    var bodyEl = document.getElementById("drilldown-modal-body");
    if (!modal || !content || !bodyEl) return;

    var queryStr = "action=" + encodeURIComponent(action);
    var titlePrefix = "";
    if (action === "user_events" && params.username) {
        queryStr += "&username=" + encodeURIComponent(params.username);
        titlePrefix = "Events for " + params.username;
    } else if (action === "ip_events" && params.ip) {
        queryStr += "&ip=" + encodeURIComponent(params.ip);
        titlePrefix = "Events from " + params.ip;
    } else if (action === "incidents") {
        titlePrefix = "Security Incidents";
    }

    titleEl.textContent = titlePrefix;
    bodyEl.innerHTML =
        '<p class="text-xs text-gray-400"><i class="fas fa-spinner fa-spin mr-1"></i>Loading...</p>';

    modal.classList.remove("hidden");
    modal.classList.add("flex");
    requestAnimationFrame(function () {
        content.classList.remove("scale-95", "opacity-0");
        content.classList.add("scale-100", "opacity-100");
    });

    var url = "/organization/" + config.orgId + "/api/security/?" + queryStr;

    fetch(url, { credentials: "same-origin" })
        .then(function (r) {
            if (!r.ok) throw new Error("Request failed with status " + r.status);
            return r.json();
        })
        .then(function (data) {
            if (data.events) {
                bodyEl.innerHTML = buildEventsTable(titlePrefix, data.events);
            } else if (data.incidents) {
                bodyEl.innerHTML = buildIncidentsTable(titlePrefix, data.incidents);
            } else if (data.error) {
                bodyEl.innerHTML =
                    '<p class="text-xs text-red-400">Error: ' + escapeHtml(data.error) + "</p>";
            } else {
                bodyEl.innerHTML = '<p class="text-xs text-gray-400">No data available</p>';
            }
        })
        .catch(function () {
            bodyEl.innerHTML = '<p class="text-xs text-red-400">Failed to load data</p>';
        });
}

function buildIncidentsTable(title, incidents) {
    var html = '<h4 class="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">' + escapeHtml(title) + "</h4>";
    html += '<table class="w-full text-xs">';
    html +=
        "<thead><tr class=\"border-b border-gray-200 dark:border-gray-700\">" +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Title</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Severity</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Status</th>' +
        '<th class="text-left py-1.5 px-2 text-gray-500 font-semibold uppercase text-[10px]">Date</th>' +
        "</tr></thead><tbody>";
    if (incidents.length === 0) {
        html +=
            '<tr><td colspan="4" class="py-4 text-center text-gray-400">No incidents found</td></tr>';
    }
    for (var i = 0; i < incidents.length; i++) {
        var inc = incidents[i];
        html +=
            '<tr class="border-b border-gray-50 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">' +
            '<td class="py-1.5 px-2 text-gray-900 dark:text-gray-100 font-medium">' +
            escapeHtml(inc.title) +
            "</td>" +
            '<td class="py-1.5 px-2">' +
            getSeverityBadge(inc.severity) +
            "</td>" +
            '<td class="py-1.5 px-2">' +
            getStatusBadge(inc.status) +
            "</td>" +
            '<td class="py-1.5 px-2 text-gray-400 text-[10px]">' +
            formatTimestamp(inc.created_at) +
            "</td></tr>";
    }
    html += "</tbody></table>";
    return html;
}

function closeDrilldownModal() {
    var modal = document.getElementById("drilldown-modal");
    var content = document.getElementById("drilldown-modal-content");
    if (!modal || !content) return;

    content.classList.remove("scale-100", "opacity-100");
    content.classList.add("scale-95", "opacity-0");
    setTimeout(function () {
        modal.classList.remove("flex");
        modal.classList.add("hidden");
    }, 200);
}

/* ── Anomaly Detail Modal ── */

function showAnomalyDetail(el) {
    var modal = document.getElementById("anomaly-detail-modal");
    var content = document.getElementById("anomaly-detail-content");
    if (!modal || !content) return;

    var severity = el.getAttribute("data-anomaly-severity") || "low";
    var severityColors = { high: "bg-red-500", medium: "bg-amber-500", low: "bg-blue-500" };
    var severityTextColors = { high: "text-red-500", medium: "text-amber-500", low: "text-blue-500" };

    var badge = document.getElementById("modal-severity-badge");
    badge.className =
        "inline-flex px-2 py-0.5 rounded text-[10px] font-bold text-white " +
        (severityColors[severity] || "bg-blue-500");
    badge.textContent = severity.charAt(0).toUpperCase() + severity.slice(1);

    document.getElementById("modal-type").textContent = el.getAttribute("data-anomaly-type") || "";
    document.getElementById("modal-user").textContent = el.getAttribute("data-anomaly-user") || "";
    document.getElementById("modal-time").textContent = el.getAttribute("data-anomaly-time") || "";
    document.getElementById("modal-ip").textContent = el.getAttribute("data-anomaly-ip") || "-";
    document.getElementById("modal-description").textContent =
        el.getAttribute("data-anomaly-description") || "";
    document.getElementById("modal-ua").textContent = el.getAttribute("data-anomaly-ua") || "-";

    var severityText = document.getElementById("modal-severity-text");
    severityText.textContent = severity.charAt(0).toUpperCase() + severity.slice(1);
    severityText.className =
        "text-xs font-semibold " + (severityTextColors[severity] || "text-blue-500");

    var anomalyId = el.getAttribute("data-anomaly-id");
    var config = window.ORG_SECURITY_CONFIG;
    var dismissBtn = document.getElementById("modal-dismiss-btn");
    dismissBtn.onclick = function () {
        closeAnomalyDetail();
        var row = document.getElementById("anomaly-row-" + anomalyId);
        if (row) {
            var btn = row.querySelector("button[title='Dismiss']");
            if (btn) dismissAnomaly(config.orgId, parseInt(anomalyId), btn);
        }
    };

    modal.classList.remove("hidden");
    modal.classList.add("flex");
    requestAnimationFrame(function () {
        content.classList.remove("scale-95", "opacity-0");
        content.classList.add("scale-100", "opacity-100");
    });
}

function closeAnomalyDetail() {
    var modal = document.getElementById("anomaly-detail-modal");
    var content = document.getElementById("anomaly-detail-content");
    if (!modal || !content) return;

    content.classList.remove("scale-100", "opacity-100");
    content.classList.add("scale-95", "opacity-0");
    setTimeout(function () {
        modal.classList.remove("flex");
        modal.classList.add("hidden");
    }, 200);
}

document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
        closeAnomalyDetail();
        closeChartModal();
        closeDrilldownModal();
    }
});

(function () {
    var sidebar = document.getElementById("anomalies-sidebar");
    if (!sidebar) return;
    sidebar.addEventListener("click", function (e) {
        var dismissBtn = e.target.closest("button[title='Dismiss']");
        if (dismissBtn) return;
        var row = e.target.closest("[data-anomaly-id]");
        if (row) showAnomalyDetail(row);
    });
})();

/* ── Dismiss Anomaly ── */

function dismissAnomaly(orgId, anomalyId, buttonEl) {
    var config = window.ORG_SECURITY_CONFIG;
    if (!config) return;

    buttonEl.disabled = true;
    buttonEl.textContent = "\u2026";

    var formData = new FormData();
    formData.append("action", "dismiss_anomaly");
    formData.append("anomaly_id", anomalyId);

    fetch("/organization/" + orgId + "/api/security/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": config.csrfToken,
            "X-Requested-With": "XMLHttpRequest",
        },
        body: formData,
    })
        .then(function (response) {
            if (!response.ok) {
                return response
                    .json()
                    .catch(function () {
                        return { error: "Request failed" };
                    })
                    .then(function (data) {
                        throw new Error(data.error || "Failed to dismiss");
                    });
            }
            return response.json();
        })
        .then(function () {
            var row = document.getElementById("anomaly-row-" + anomalyId);
            if (row) {
                row.style.transition = "opacity 0.3s";
                row.style.opacity = "0";
                setTimeout(function () {
                    row.remove();
                }, 300);
            }
        })
        .catch(function (err) {
            buttonEl.disabled = false;
            buttonEl.innerHTML = '<i class="fas fa-times text-[9px]"></i>';
            var errorSpan = document.createElement("span");
            errorSpan.className = "text-[9px] text-red-500 ml-1";
            errorSpan.textContent = err.message;
            buttonEl.parentNode.appendChild(errorSpan);
            setTimeout(function () {
                if (errorSpan.parentNode) {
                    errorSpan.parentNode.removeChild(errorSpan);
                }
            }, 5000);
        });
}

/* ── Utility Functions ── */

function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str || ""));
    return div.innerHTML;
}

function getTypeBadge(type) {
    var lower = (type || "").toLowerCase();
    if (lower === "login") {
        return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Login</span>';
    } else if (lower.indexOf("fail") !== -1) {
        return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">Failed</span>';
    }
    return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">Logout</span>';
}

function getSeverityBadge(severity) {
    var lower = (severity || "").toLowerCase();
    if (lower === "critical") {
        return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">Critical</span>';
    } else if (lower === "high") {
        return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">High</span>';
    } else if (lower === "medium") {
        return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">Medium</span>';
    }
    return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">Low</span>';
}

function getStatusBadge(status) {
    var lower = (status || "").toLowerCase();
    if (lower === "open") {
        return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">Open</span>';
    } else if (lower === "investigating") {
        return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">Investigating</span>';
    }
    return '<span class="inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Resolved</span>';
}

function formatTimestamp(isoStr) {
    if (!isoStr) return "-";
    try {
        var d = new Date(isoStr);
        if (Number.isNaN(d.getTime())) return "-";
        var now = new Date();
        var diff = Math.max(0, Math.floor((now - d) / 1000));
        if (diff < 60) return diff + "s ago";
        if (diff < 3600) return Math.floor(diff / 60) + "m ago";
        if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
        return Math.floor(diff / 86400) + "d ago";
    } catch (e) {
        return "-";
    }
}
