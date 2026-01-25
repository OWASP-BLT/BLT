/**
 * Shared JavaScript functionality for issue reporting admin pages
 */

let currentReportId = null;

function showReportDetails(reportId, description, adminNotes, status) {
    currentReportId = reportId;
    document.getElementById('reportDetailsDescription').textContent = description;
    document.getElementById('adminNotes').value = adminNotes;
    document.getElementById('reportStatus').value = status;
    document.getElementById('reportDetailsModal').classList.remove('hidden');
}

function closeReportDetailsModal() {
    document.getElementById('reportDetailsModal').classList.add('hidden');
    currentReportId = null;
}

function getStatusClass(status) {
    const classes = {
        'pending': 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-200',
        'reviewed': 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-200',
        'resolved': 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-200',
        'dismissed': 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-200'
    };
    return classes[status] || '';
}

function getStatusColor(status) {
    const colors = {
        'pending': 'red',
        'reviewed': 'blue',
        'resolved': 'green',
        'dismissed': 'gray'
    };
    return colors[status] || 'gray';
}

function updatePendingCount(newStatus) {
    if (newStatus !== 'pending') {
        const pendingCountEl = document.querySelector('.bg-red-100');
        if (pendingCountEl) {
            const currentCount = parseInt(pendingCountEl.textContent.split(' ')[0]);
            if (currentCount > 1) {
                pendingCountEl.textContent = `${currentCount - 1} Pending`;
            } else {
                pendingCountEl.textContent = '0 Pending';
                // Hide the element if it's in the specific reports page
                if (window.location.pathname.includes('specific')) {
                    pendingCountEl.style.display = 'none';
                }
            }
        }
    }
}

// Function for the main reports table
function updateReportStatus(reportId, status) {
    const formData = new FormData();
    formData.append('status', status);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

    fetch(`/issue-reports/${reportId}/update/`, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Update the status badge and text dynamically
            const reportRow = document.querySelector(`tr[data-report-id="${reportId}"]`);
            if (reportRow) {
                const statusBadge = reportRow.querySelector('.status-badge');
                statusBadge.className = `px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusClass(status)}`;
                statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
                updatePendingCount(status);
            }
        } else {
            alert(data.message || 'Failed to update report');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to update report. Please try again.');
    });
}

// Function for the modal save
function saveReportUpdate() {
    if (!currentReportId) return;

    const formData = new FormData();
    const newStatus = document.getElementById('reportStatus').value;
    formData.append('status', newStatus);
    formData.append('admin_notes', document.getElementById('adminNotes').value);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

    fetch(`/issue-reports/${currentReportId}/update/`, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Check if we're on the main reports page or specific reports page
            const reportRow = document.querySelector(`tr[data-report-id="${currentReportId}"]`);
            const reportCard = document.querySelector(`[data-report-id="${currentReportId}"]`);
            
            if (reportRow) {
                // Main reports page - update table row
                const statusBadge = reportRow.querySelector('.status-badge');
                statusBadge.className = `px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusClass(newStatus)}`;
                statusBadge.textContent = newStatus.charAt(0).toUpperCase() + newStatus.slice(1);
            } else if (reportCard) {
                // Specific reports page - update card
                const statusBadge = reportCard.querySelector('.status-badge');
                reportCard.className = reportCard.className.replace(/border-\w+-\d+/, `border-${getStatusColor(newStatus)}-500`);
                statusBadge.className = `px-2 py-1 text-xs font-semibold rounded-full ${getStatusClass(newStatus)}`;
                statusBadge.textContent = newStatus.charAt(0).toUpperCase() + newStatus.slice(1);
            }
            
            updatePendingCount(newStatus);
            closeReportDetailsModal();
        } else {
            alert(data.message || 'Failed to update report');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to update report. Please try again.');
    });
}