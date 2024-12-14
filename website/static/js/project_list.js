document.addEventListener('DOMContentLoaded', function() {
    // Modal handling
    const modals = {
        addProject: document.getElementById('addProjectModal'),
        addRepo: document.getElementById('addRepoModal'),
        filter: document.getElementById('filterModal')
    };

    // Show modal function
    function showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            // Use requestAnimationFrame to ensure display takes effect
            requestAnimationFrame(() => {
                modal.classList.add('show');
            });
            document.body.style.overflow = 'hidden';
        }
    }

    // Hide modal function
    function hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            // Wait for animation to complete
            setTimeout(() => {
                modal.style.display = 'none';
                document.body.style.overflow = '';
            }, 300);
        }
    }

    // Close modal when clicking outside
    window.onclick = function(event) {
        for (let modalId in modals) {
            const modal = modals[modalId];
            if (event.target === modal) {
                hideModal(modal.id);
            }
        }
    }

    // Add click handlers for modal triggers
    document.querySelectorAll('[data-toggle="modal"]').forEach(button => {
        button.addEventListener('click', function() {
            const targetModal = this.getAttribute('data-target').replace('#', '');
            showModal(targetModal);
        });
    });

    // Add click handlers for modal close buttons
    document.querySelectorAll('.modal .close').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            hideModal(modal.id);
        });
    });

    // Form submissions
    const addProjectForm = document.querySelector('#addProjectModal form');
    if (addProjectForm) {
        addProjectForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    body: new FormData(this),
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });

                if (response.ok) {
                    // Refresh the page to show the new project
                    window.location.reload();
                } else {
                    const data = await response.json();
                    showError(data.error || 'Failed to add project');
                }
            } catch (error) {
                showError('An error occurred while adding the project');
            }
        });
    }

    const addRepoForm = document.querySelector('#addRepoModal form');
    if (addRepoForm) {
        addRepoForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    body: new FormData(this),
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });

                if (response.ok) {
                    window.location.reload();
                } else {
                    const data = await response.json();
                    showError(data.error || 'Failed to add repository');
                }
            } catch (error) {
                showError('An error occurred while adding the repository');
            }
        });
    }

    // Filter form handling
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const searchParams = new URLSearchParams();

            for (let [key, value] of formData.entries()) {
                if (value) {  // Only add non-empty values
                    searchParams.append(key, value);
                }
            }

            // Preserve existing page number if any
            const currentPage = new URLSearchParams(window.location.search).get('page');
            if (currentPage) {
                searchParams.append('page', currentPage);
            }

            window.location.href = `${window.location.pathname}?${searchParams.toString()}`;
        });

        // Handle reset button
        const resetButton = filterForm.querySelector('button[type="reset"]');
        if (resetButton) {
            resetButton.addEventListener('click', function(e) {
                e.preventDefault();
                window.location.href = window.location.pathname;
            });
        }
    }

    // Error message display
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.textContent = message;
        
        const container = document.querySelector('.container');
        container.insertBefore(errorDiv, container.firstChild);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    // Add some basic animations
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('show.bs.modal', function() {
            this.style.opacity = 0;
            setTimeout(() => {
                this.style.opacity = 1;
            }, 10);
        });
    });

    // Handle filter type selection
    const filterTypeSelect = document.getElementById('filterTypeSelect');
    const projectFilters = document.querySelector('.project-filters');
    const repoFilters = document.querySelector('.repo-filters');

    if (filterTypeSelect) {
        filterTypeSelect.addEventListener('change', function() {
            const selectedValue = this.value;
            
            if (selectedValue === 'projects') {
                projectFilters.style.display = 'block';
                repoFilters.style.display = 'none';
            } else if (selectedValue === 'repos') {
                projectFilters.style.display = 'none';
                repoFilters.style.display = 'block';
            } else {
                projectFilters.style.display = 'block';
                repoFilters.style.display = 'block';
            }
        });

        // Trigger change event on load to set initial state
        filterTypeSelect.dispatchEvent(new Event('change'));
    }

    // Add smooth scrolling for pagination
    document.querySelectorAll('.pagination a').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            // Navigate after scroll animation
            setTimeout(() => {
                window.location.href = href;
            }, 500);
        });
    });
}); 