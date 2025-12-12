// Initialize global data object
window.gsocData = {
    summary: {},
    yearlyChart: {},
    topReposChart: {},
    reportData: []
};

// Helper function to parse escaped JSON
function parseEscapedJSON(str) {
    if (!str) return {};

    try {
        let fixed = str.replace(/\\\\/g, '\\');
        fixed = fixed.replace(/\\u([0-9A-Fa-f]{4})/g, (_, hex) =>
            String.fromCharCode(parseInt(hex, 16))
        );
        return JSON.parse(fixed);
    } catch (e) {
        return {};
    }
}

// Parse data from hidden div
function parseDataFromDOM() {
    const dataDiv = document.getElementById('gsocData');
    if (dataDiv) {
        try {
            window.gsocData.summary = parseEscapedJSON(dataDiv.dataset.summary);
            window.gsocData.yearlyChart = parseEscapedJSON(dataDiv.dataset.yearlyChart);
            window.gsocData.topReposChart = parseEscapedJSON(dataDiv.dataset.topRepos);
            window.gsocData.reportData = parseEscapedJSON(dataDiv.dataset.reportData);
        } catch (e) {
            // Silent error handling
        }
    }
}

function parseDataDirectly() {
    const dataDiv = document.getElementById('gsocData');
    if (dataDiv) {
        const summary = dataDiv.getAttribute('data-summary');
        const yearlyChart = dataDiv.getAttribute('data-yearly-chart');
        const topRepos = dataDiv.getAttribute('data-top-repos');
        const reportData = dataDiv.getAttribute('data-report-data');
        
        window.gsocData.summary = parseEscapedJSON(summary);
        window.gsocData.yearlyChart = parseEscapedJSON(yearlyChart);
        window.gsocData.topReposChart = parseEscapedJSON(topRepos);
        window.gsocData.reportData = parseEscapedJSON(reportData);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    parseDataFromDOM();
    
    if (Object.keys(window.gsocData.yearlyChart).length === 0 && 
        Object.keys(window.gsocData.topReposChart).length === 0) {
        parseDataDirectly();
    }
    
    // Process Yearly Chart Data
    let yearlyCategories = [];
    let yearlySeriesData = [];
    
    if (window.gsocData.yearlyChart) {
        if (Array.isArray(window.gsocData.yearlyChart)) {
            yearlyCategories = window.gsocData.yearlyChart.map(item => String(item.year || item.label || item.name));
            yearlySeriesData = window.gsocData.yearlyChart.map(item => Number(item.prs || item.value || item.count || 0));
        } else if (window.gsocData.yearlyChart.years && window.gsocData.yearlyChart.pr_counts) {
            yearlyCategories = window.gsocData.yearlyChart.years.map(String);
            yearlySeriesData = window.gsocData.yearlyChart.pr_counts.map(Number);
        } else if (window.gsocData.yearlyChart.labels && window.gsocData.yearlyChart.data) {
            yearlyCategories = window.gsocData.yearlyChart.labels.map(String);
            yearlySeriesData = window.gsocData.yearlyChart.data.map(Number);
        } else {
            const keys = Object.keys(window.gsocData.yearlyChart);
            if (keys.length > 0) {
                yearlyCategories = keys;
                yearlySeriesData = keys.map(key => Number(window.gsocData.yearlyChart[key]) || 0);
            }
        }
    }
    
    const yearlyChartElement = document.querySelector("#yearlyPrChart");
    if (yearlyChartElement) {
        if (yearlyCategories.length > 0 && yearlySeriesData.length > 0) {
            const maxValue = Math.max(...yearlySeriesData);
            const yAxisMax = Math.ceil(maxValue * 1.1);
            
            const isDarkMode = document.documentElement.classList.contains('dark');
            const textColor = isDarkMode ? '#E5E7EB' : '#374151';
            const gridColor = isDarkMode ? '#4B5563' : '#E5E7EB';
            const labelColor = isDarkMode ? '#9CA3AF' : '#6B7280';
            
            const yearlyOptions = {
                chart: { 
                    type: 'bar', 
                    height: 350,
                    toolbar: { 
                        show: true,
                        tools: {
                            download: true,
                            selection: true,
                            zoom: true,
                            zoomin: true,
                            zoomout: true,
                            pan: true,
                            reset: true
                        }
                    },
                    background: 'transparent',
                    foreColor: textColor
                },
                states: {
                    normal: { filter: { type: 'none' } }, 
                    hover: { filter: { type: 'none' } },
                    active: { filter: { type: 'none' } }
                },
                series: [{
                    name: 'PR Count',
                    data: yearlySeriesData
                }],
                xaxis: {
                    categories: yearlyCategories,
                    title: {
                        text: 'Year',
                        style: { 
                            color: labelColor,
                            fontSize: '12px',
                            fontWeight: 600
                        }
                    },
                    labels: {
                        style: {
                            colors: labelColor,
                            fontSize: '11px',
                            fontWeight: 500
                        }
                    },
                    axisBorder: {
                        show: true,
                        color: gridColor
                    },
                    axisTicks: {
                        show: true,
                        color: gridColor
                    }
                },
                yaxis: {
                    title: {
                        text: 'Number of PRs',
                        style: { 
                            color: labelColor,
                            fontSize: '12px',
                            fontWeight: 600
                        }
                    },
                    min: 0,
                    max: yAxisMax,
                    forceNiceScale: true,
                    tickAmount: 5,
                    labels: {
                        style: {
                            colors: labelColor,
                            fontSize: '11px'
                        },
                        formatter: function(val) {
                            return Math.round(val);
                        }
                    },
                    axisBorder: {
                        show: true,
                        color: gridColor
                    }
                },
                colors: ['#DC2626'],
                plotOptions: {
                    bar: {
                        borderRadius: 6,
                        columnWidth: '60%',
                        distributed: false,
                        dataLabels: {
                            position: 'top'
                        }
                    }
                },
                dataLabels: {
                    enabled: true,
                    offsetY: -20,
                    style: {
                        fontSize: '11px',
                        fontWeight: 600,
                        colors: [textColor]
                    },
                    background: {
                        enabled: false
                    },
                    formatter: function(val) {
                        return val;
                    }
                },
                grid: {
                    borderColor: gridColor,
                    strokeDashArray: 4,
                    xaxis: {
                        lines: {
                            show: false
                        }
                    },
                    yaxis: {
                        lines: {
                            show: true
                        }
                    }
                },
                tooltip: {
                    theme: isDarkMode ? 'dark' : 'light',
                    style: {
                        fontSize: '12px'
                    },
                    y: {
                        formatter: function(val) {
                            return val + ' PRs';
                        },
                        title: {
                            formatter: function() {
                                return 'Count:';
                            }
                        }
                    }
                }
            };
            
            try {
                const yearlyChart = new ApexCharts(yearlyChartElement, yearlyOptions);
                yearlyChart.render();
                window.yearlyApexChart = yearlyChart; // Store for PDF generation
            } catch (e) {
                yearlyChartElement.innerHTML = 
                    '<div class="text-center py-8 text-red-500">Error loading yearly chart</div>';
            }
        } else {
            yearlyChartElement.innerHTML = 
                '<div class="text-center py-8 text-gray-500">No yearly data available for the selected period</div>';
        }
    }
    
    // Process Top Repos Data
    let topReposLabels = [];
    let topReposSeries = [];
    
    if (window.gsocData.topReposChart) {
        if (Array.isArray(window.gsocData.topReposChart)) {
            topReposLabels = window.gsocData.topReposChart.map(item => 
                String(item.repo || item.label || item.name || 'Unknown').substring(0, 30)
            );
            topReposSeries = window.gsocData.topReposChart.map(item => 
                Number(item.prs || item.value || item.count || 0)
            );
        } else if (window.gsocData.topReposChart.repos && window.gsocData.topReposChart.counts) {
            topReposLabels = window.gsocData.topReposChart.repos.map(name => 
                String(name).substring(0, 30)
            );
            topReposSeries = window.gsocData.topReposChart.counts.map(Number);
        } else if (window.gsocData.topReposChart.labels && window.gsocData.topReposChart.data) {
            topReposLabels = window.gsocData.topReposChart.labels.map(name => 
                String(name).substring(0, 30)
            );
            topReposSeries = window.gsocData.topReposChart.data.map(Number);
        }
    }
    
    // Top Repositories Chart - IMPROVED VISUALS
    const topReposChartElement = document.querySelector("#topReposChart");
    if (topReposChartElement) {
        if (topReposLabels.length > 0 && topReposSeries.length > 0) {
            const isDarkMode = document.documentElement.classList.contains('dark');
            const textColor = isDarkMode ? '#E5E7EB' : '#374151';
            const labelColor = isDarkMode ? '#9CA3AF' : '#6B7280';
            
            const topReposOptions = {
                chart: { 
                    type: 'donut', 
                    height: 350,
                    background: 'transparent',
                    foreColor: textColor
                },
                series: topReposSeries,
                labels: topReposLabels,
                colors: ['#DC2626', '#EF4444', '#F87171', '#FCA5A5', '#FECACA', '#FEE2E2'],
                plotOptions: {
                    pie: {
                        donut: {
                            size: '55%',
                            labels: {
                                show: true,
                                name: {
                                    show: true,
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    color: textColor
                                },
                                value: {
                                    show: true,
                                    fontSize: '20px',
                                    fontWeight: 700,
                                    color: textColor,
                                    formatter: function(val) {
                                        return val;
                                    }
                                },
                                total: {
                                    show: true,
                                    showAlways: true,
                                    label: 'Total PRs',
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    color: labelColor,
                                    formatter: function(w) {
                                        return w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                                    }
                                }
                            }
                        }
                    }
                },
                legend: {
                    position: 'bottom',
                    horizontalAlign: 'center',
                    fontSize: '12px',
                    fontWeight: 500,
                    labels: {
                        colors: labelColor,
                        useSeriesColors: false
                    },
                    itemMargin: {
                        horizontal: 10,
                        vertical: 5
                    }
                },
                dataLabels: {
                    enabled: true,
                    formatter: function(val, opts) {
                        return Math.round(val) + '%';
                    },
                    style: {
                        fontSize: '11px',
                        fontWeight: 600,
                        colors: ['#FFFFFF']
                    },
                    dropShadow: {
                        enabled: true,
                        top: 1,
                        left: 1,
                        blur: 2,
                        color: '#000000',
                        opacity: 0.3
                    }
                },
                tooltip: {
                    theme: isDarkMode ? 'dark' : 'light',
                    style: {
                        fontSize: '12px'
                    },
                    y: {
                        formatter: function(value) {
                            return value + ' PRs';
                        },
                        title: {
                            formatter: function(seriesName) {
                                return seriesName;
                            }
                        }
                    }
                },
                responsive: [{
                    breakpoint: 480,
                    options: {
                        chart: {
                            height: 300
                        },
                        legend: {
                            position: 'bottom'
                        }
                    }
                }]
            };
            
            try {
                const topReposChart = new ApexCharts(topReposChartElement, topReposOptions);
                topReposChart.render();
                window.topReposApexChart = topReposChart; // Store for PDF generation
            } catch (e) {
                topReposChartElement.innerHTML = 
                    '<div class="text-center py-8 text-red-500">Error loading repository chart</div>';
            }
        } else {
            topReposChartElement.innerHTML = 
                '<div class="text-center py-8 text-gray-500">No repository data available</div>';
        }
    }
});

// Export Charts Data
function exportChartData() {
    const data = {
        yearlyData: window.gsocData.yearlyChart,
        topReposData: window.gsocData.topReposChart,
        reportData: window.gsocData.reportData,
        summary: window.gsocData.summary
    };
    
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `gsoc_pr_report_${new Date().toISOString().split('T')[0]}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    document.body.removeChild(downloadAnchor);
}

// Download Report as PDF
async function downloadReport(event) {
    try {
        // Show loading state
        const button = event.target.closest('button');
        const originalText = button.innerHTML;
        button.innerHTML = '<svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Generating PDF...';
        button.disabled = true;
        
        // Include jsPDF and html2canvas libraries dynamically
        await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js');
        await loadScript('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js');
        
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('p', 'mm', 'a4');
        
        // Add title
        doc.setFontSize(20);
        doc.setTextColor(220, 38, 38); // Red color
        doc.text('GSOC PR Analysis Report', 105, 20, { align: 'center' });
        
        // Add subtitle
        doc.setFontSize(12);
        doc.setTextColor(100, 100, 100);
        doc.text(`Pull requests merged during GSOC periods (${window.gsocData.summary.start_year || 'N/A'} - ${window.gsocData.summary.end_year || 'N/A'})`, 105, 30, { align: 'center' });
        
        // Add summary section
        doc.setFontSize(14);
        doc.setTextColor(0, 0, 0);
        doc.text('Summary Statistics', 20, 45);
        
        // Summary boxes
        doc.setDrawColor(220, 38, 38);
        doc.setFillColor(255, 255, 255);
        
        // Total Years
        doc.rect(20, 50, 40, 20, 'FD');
        doc.setFontSize(10);
        doc.setTextColor(100, 100, 100);
        doc.text('Total Years', 40, 55, { align: 'center' });
        doc.setFontSize(16);
        doc.setTextColor(0, 0, 0);
        doc.text(window.gsocData.summary.total_years || '0', 40, 65, { align: 'center' });
        
        // Total Repos
        doc.rect(65, 50, 40, 20, 'FD');
        doc.setFontSize(10);
        doc.setTextColor(100, 100, 100);
        doc.text('Active Repos', 85, 55, { align: 'center' });
        doc.setFontSize(16);
        doc.setTextColor(0, 0, 0);
        doc.text(window.gsocData.summary.total_repos || '0', 85, 65, { align: 'center' });
        
        // Total PRs
        doc.rect(110, 50, 40, 20, 'FD');
        doc.setFontSize(10);
        doc.setTextColor(100, 100, 100);
        doc.text('Total PRs', 130, 55, { align: 'center' });
        doc.setFontSize(16);
        doc.setTextColor(0, 0, 0);
        doc.text(window.gsocData.summary.total_prs || '0', 130, 65, { align: 'center' });
        
        // Avg PRs/Year
        doc.rect(155, 50, 40, 20, 'FD');
        doc.setFontSize(10);
        doc.setTextColor(100, 100, 100);
        doc.text('Avg PRs/Year', 175, 55, { align: 'center' });
        doc.setFontSize(16);
        doc.setTextColor(0, 0, 0);
        doc.text(window.gsocData.summary.avg_prs_per_year || '0', 175, 65, { align: 'center' });
        
        // Add charts section
        doc.addPage();
        doc.setFontSize(14);
        doc.setTextColor(0, 0, 0);
        doc.text('Yearly PR Contributions', 20, 20);
        
        // Add yearly chart image if available
        if (window.yearlyApexChart) {
            try {
                const yearlyChartImg = await window.yearlyApexChart.dataURI();
                doc.addImage(yearlyChartImg.imgURI, 'PNG', 20, 30, 170, 80);
            } catch (e) {
                doc.text('Yearly chart not available', 20, 40);
            }
        }
        
        doc.text('Top Repositories', 20, 130);
        
        // Add top repos chart image if available
        if (window.topReposApexChart) {
            try {
                const topReposChartImg = await window.topReposApexChart.dataURI();
                doc.addImage(topReposChartImg.imgURI, 'PNG', 20, 140, 170, 80);
            } catch (e) {
                doc.text('Top repositories chart not available', 20, 150);
            }
        }
        
        // Add detailed data
        if (window.gsocData.reportData && window.gsocData.reportData.length > 0) {
            doc.addPage();
            doc.setFontSize(16);
            doc.setTextColor(220, 38, 38);
            doc.text('Year-by-Year Analysis', 20, 20);
            
            let yPosition = 30;
            window.gsocData.reportData.forEach((year, index) => {
                if (yPosition > 250) {
                    doc.addPage();
                    yPosition = 20;
                }
                
                doc.setFontSize(12);
                doc.setTextColor(0, 0, 0);
                doc.text(`GSOC ${year.year} (${year.total_prs || 0} PRs, ${year.repos?.length || 0} Repositories)`, 20, yPosition);
                yPosition += 10;
                
                if (year.repos && year.repos.length > 0) {
                    doc.setFontSize(9);
                    year.repos.forEach((repo, repoIndex) => {
                        if (yPosition > 270) {
                            doc.addPage();
                            yPosition = 20;
                        }
                        doc.text(`• ${repo.repo__name || 'Unknown'}: ${repo.pr_count || 0} PRs (${repo.unique_contributors || 0} contributors)`, 25, yPosition);
                        yPosition += 7;
                    });
                }
                yPosition += 5;
            });
        }
        
        // Add footer
        const totalPages = doc.internal.getNumberOfPages();
        for (let i = 1; i <= totalPages; i++) {
            doc.setPage(i);
            doc.setFontSize(8);
            doc.setTextColor(150, 150, 150);
            doc.text(`Page ${i} of ${totalPages}`, 105, 287, { align: 'center' });
            doc.text(`Generated on ${new Date().toLocaleDateString()}`, 105, 292, { align: 'center' });
            doc.text('GSOC PR Analysis Report', 20, 292);
        }
        
        // Save the PDF
        const fileName = `gsoc_pr_report_${window.gsocData.summary.start_year || ''}_${window.gsocData.summary.end_year || ''}_${new Date().toISOString().split('T')[0]}.pdf`;
        doc.save(fileName);
        
        // Restore button state
        button.innerHTML = originalText;
        button.disabled = false;
        
    } catch (error) {
        alert('Error generating PDF report. Please try again.');
        
        // Restore button state on error
        const button = event.target.closest('button');
        button.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg> Download Report';
        button.disabled = false;
    }
}

// Helper function to load external scripts
function loadScript(src) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) {
            resolve();
            return;
        }
        
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Alternative simple HTML report download
function downloadHTMLReport() {
    const reportData = window.gsocData;
    
    // Create HTML content
    let htmlContent = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>GSOC PR Analysis Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
                h1 { color: #DC2626; border-bottom: 2px solid #DC2626; padding-bottom: 10px; }
                h2 { color: #444; margin-top: 30px; }
                .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }
                .summary-box { border: 1px solid #DC2626; border-radius: 5px; padding: 15px; text-align: center; }
                .summary-label { font-size: 14px; color: #666; }
                .summary-value { font-size: 24px; font-weight: bold; color: #DC2626; margin: 10px 0; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th { background-color: #DC2626; color: white; padding: 12px; text-align: left; }
                td { padding: 10px; border-bottom: 1px solid #ddd; }
                tr:hover { background-color: #f5f5f5; }
                .year-section { margin-bottom: 40px; }
                .year-header { background-color: #f8f9fa; padding: 15px; border-left: 4px solid #DC2626; margin: 20px 0; }
                .chart-placeholder { background-color: #f8f9fa; padding: 20px; text-align: center; margin: 20px 0; color: #666; }
                .footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }
                @media print {
                    .no-print { display: none; }
                    body { margin: 20px; }
                }
</style>
        </head>
        <body>
            <h1>Google Summer of Code - PR Analysis Report</h1>
            <p><strong>Period:</strong> ${reportData.summary.start_year || 'N/A'} - ${reportData.summary.end_year || 'N/A'}</p>
            <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
            
            <div class="summary">
                <div class="summary-box">
                    <div class="summary-label">Total Years</div>
                    <div class="summary-value">${reportData.summary.total_years || '0'}</div>
                </div>
                <div class="summary-box">
                    <div class="summary-label">Active Repositories</div>
                    <div class="summary-value">${reportData.summary.total_repos || '0'}</div>
                </div>
                <div class="summary-box">
                    <div class="summary-label">Total PRs</div>
                    <div class="summary-value">${reportData.summary.total_prs || '0'}</div>
                </div>
                <div class="summary-box">
                    <div class="summary-label">Avg PRs/Year</div>
                    <div class="summary-value">${reportData.summary.avg_prs_per_year || '0'}</div>
                </div>
            </div>
            
            <div class="chart-placeholder">
                <h3>Yearly PR Contributions Chart</h3>
                <p>Chart data exported separately</p>
            </div>
            
            <div class="chart-placeholder">
                <h3>Top Repositories Chart</h3>
                <p>Chart data exported separately</p>
            </div>
            
            <h2>Year-by-Year Analysis</h2>
    `;
    
    // Add yearly data
    if (reportData.reportData && Array.isArray(reportData.reportData)) {
        reportData.reportData.forEach(year => {
            htmlContent += `
                <div class="year-section">
                    <div class="year-header">
                        <h3>GSOC ${year.year} (May - September)</h3>
                        <p>Total PRs: ${year.total_prs || 0} | Repositories: ${year.repos?.length || 0}</p>
                    </div>
            `;
            
            if (year.repos && year.repos.length > 0) {
                htmlContent += `
                    <table>
                        <thead>
                            <tr>
                                <th>Repository</th>
                                <th>PR Count</th>
                                <th>Contributors</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                year.repos.forEach(repo => {
                    htmlContent += `
                        <tr>
                            <td>${repo.repo__name || 'Unknown'}</td>
                            <td>${repo.pr_count || 0}</td>
                            <td>${repo.unique_contributors || 0}</td>
                        </tr>
                    `;
                });
                
                htmlContent += `
                        </tbody>
                    </table>
                `;
            } else {
                htmlContent += `<p>No pull requests found for this year.</p>`;
            }
            
            htmlContent += `</div>`;
        });
    } else {
        htmlContent += `<p>No yearly data available.</p>`;
    }
    
    // Close HTML
    htmlContent += `
            <div class="footer">
                <p>Report generated by GSOC PR Analysis Tool</p>
                <p>Data covers GSOC periods (May - September) for each year</p>
            </div>
        </body>
        </html>
    `;
    
    // Create and trigger download
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gsoc_pr_report_${reportData.summary.start_year || ''}_${reportData.summary.end_year || ''}_${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
function viewRawData() {
    const dataWindow = window.open('', '_blank');

    if (dataWindow) {
        dataWindow.document.write(
            '<pre>' + JSON.stringify(window.gsocData, null, 2) + '</pre>'
                );
                dataWindow.document.close();
            } else {
                alert('Popup blocked. Please allow popups for this site.');
            }
        }
    