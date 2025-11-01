// Education page delete functionality
function confirmDelete(type, id, title) {
    const modal = document.getElementById('deleteModal');
    const confirmText = document.getElementById('deleteConfirmText');
    const form = document.getElementById('deleteForm');
    
    if (type === 'course') {
        confirmText.textContent = `Are you sure you want to delete the course "${title}"? This will also delete all sections and lectures within this course.`;
        form.action = `/education/courses/${id}/delete/`;
    } else if (type === 'lecture') {
        confirmText.textContent = `Are you sure you want to delete the lecture "${title}"?`;
        form.action = `/education/standalone-lectures/${id}/delete/`;
    }
    
    modal.classList.remove('hidden');
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    modal.classList.add('hidden');
}

// Close modal when clicking outside of it
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeDeleteModal();
            }
        });
    }
});
