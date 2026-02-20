document.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined") {
        return;
    }

    var config = window.ORG_SECURITY_CONFIG;
    if (!config) return;

    initRiskGauge(config.riskScore);
    initSeverityChart(config.severityLabels, config.severityCounts);
    initHourlyChart(config.hourlyData);
});

function initRiskGauge(riskScore) {
    var ctx = document.getElementById("riskGaugeChart");
    if (!ctx) return;

    var score = Math.max(0, Math.min(100, riskScore || 0));
    var color =
        score >= 70
            ? "#e74c3c"
            : score >= 40
              ? "#f59e0b"
              : "#22c55e";
    var remaining = 100 - score;

    new Chart(ctx, {
        type: "doughnut",
        data: {
            datasets: [
                {
                    data: [score, remaining],
                    backgroundColor: [color, "#e5e7eb"],
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

function initSeverityChart(labels, counts) {
    var ctx = document.getElementById("severityChart");
    if (!ctx) return;
    if (!Array.isArray(labels) || !Array.isArray(counts)) return;

    var colors = ["#e74c3c", "#f97316", "#f59e0b", "#3b82f6"];

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    data: counts,
                    backgroundColor: colors,
                    borderRadius: 4,
                    barThickness: 28,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: "#9ca3af",
                    },
                    grid: { display: false },
                },
                y: {
                    ticks: {
                        color: "#9ca3af",
                    },
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
                    backgroundColor: "#3b82f6",
                    borderRadius: 2,
                    barThickness: 8,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    ticks: {
                        color: "#9ca3af",
                        maxRotation: 0,
                        callback: function (val, index) {
                            return index % 4 === 0 ? this.getLabelForValue(val) : "";
                        },
                    },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: "#9ca3af",
                    },
                    grid: { color: "#f3f4f6" },
                },
            },
        },
    });
}

function dismissAnomaly(orgId, anomalyId, buttonEl) {
    var config = window.ORG_SECURITY_CONFIG;
    if (!config) return;

    buttonEl.disabled = true;
    buttonEl.textContent = "Dismissing\u2026";

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
            buttonEl.textContent = "Dismiss";
            var errorSpan = document.createElement("span");
            errorSpan.className = "text-xs text-red-500 ml-2";
            errorSpan.textContent = err.message;
            buttonEl.parentNode.appendChild(errorSpan);
            setTimeout(function () {
                if (errorSpan.parentNode) {
                    errorSpan.parentNode.removeChild(errorSpan);
                }
            }, 5000);
        });
}
