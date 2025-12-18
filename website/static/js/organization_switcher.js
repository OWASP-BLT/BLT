/**
 * Organization Switcher JavaScript
 * Handles switching between organizations in the dashboard
 */

(function() {
    'use strict';

    // Map of URL names to their URL patterns
    const urlPatterns = {
        'organization_analytics': '/organization/{id}/dashboard/analytics/',
        'organization_team_overview': '/organization/{id}/dashboard/team-overview/',
        'organization_manage_bugs': '/organization/{id}/dashboard/bugs/',
        'organization_manage_domains': '/organization/{id}/dashboard/domains/',
        'organization_manage_bughunts': '/organization/{id}/dashboard/bughunts/',
        'organization_manage_roles': '/organization/{id}/dashboard/roles/',
        'organization_manage_integrations': '/organization/{id}/dashboard/integrations/',
        'organization_manage_jobs': '/organization/{id}/dashboard/jobs/',
        'add_domain': '/organization/{id}/dashboard/add_domain/',
        'edit_domain': '/organization/{id}/dashboard/edit_domain/',
        'add_bughunt': '/organization/{id}/dashboard/add_bughunt/',
        'add_slack_integration': '/organization/{id}/dashboard/add_slack_integration/',
        'create_job': '/organization/{id}/jobs/create/',
        'edit_job': '/organization/{id}/jobs/edit/',
    };

    /**
     * Get the URL for a given organization ID and current URL name
     * @param {number} orgId - The organization ID
     * @param {string} urlName - The current URL name
     * @returns {string} The constructed URL
     */
    function getOrganizationUrl(orgId, urlName) {
        // Check if we have a pattern for this URL name
        if (urlPatterns[urlName]) {
            return urlPatterns[urlName].replace('{id}', orgId);
        }

        // Fallback: try to construct from current path
        const currentPath = window.location.pathname;
        const pathParts = currentPath.split('/');
        
        // Find the organization ID in the path (should be after 'organization')
        const orgIndex = pathParts.indexOf('organization');
        if (orgIndex !== -1 && pathParts[orgIndex + 1]) {
            // Replace the organization ID
            pathParts[orgIndex + 1] = orgId;
    
            // Check if this is an edit_job page and preserve the job_id
            const editJobIndex = pathParts.indexOf('edit_job');
            if (editJobIndex !== -1 && pathParts[editJobIndex + 1]) {
                // The job_id is already in the path, just return the reconstructed path
                return pathParts.join('/');
            }
    
            return pathParts.join('/');
        }

        // Ultimate fallback: redirect to analytics page
        return `/organization/${orgId}/dashboard/analytics/`;
    }

    /**
     * Initialize the organization switcher
     */
    function initOrganizationSwitcher() {
        const switcherButton = document.getElementById('org-switcher-button');
        const switcherDropdown = document.getElementById('org-switcher-dropdown');
        const switcherChevron = document.getElementById('org-switcher-chevron');
        const switcherItems = document.querySelectorAll('.org-switcher-item');

        if (!switcherButton || !switcherDropdown || !switcherChevron) {
            return;
        }

        // Toggle dropdown on button click
        switcherButton.addEventListener('click', function(e) {
            e.stopPropagation();
            const isHidden = switcherDropdown.classList.contains('hidden');
            
            if (isHidden) {
                switcherDropdown.classList.remove('hidden');
                switcherChevron.classList.add('rotate-180');
            } else {
                switcherDropdown.classList.add('hidden');
                switcherChevron.classList.remove('rotate-180');
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            const container = document.getElementById('org-switcher-container');
            if (container && !container.contains(e.target)) {
                switcherDropdown.classList.add('hidden');
                switcherChevron.classList.remove('rotate-180');
            }
        });

        // Handle organization selection
        switcherItems.forEach(function(item) {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const orgId = parseInt(this.getAttribute('data-org-id'));
                const orgName = this.getAttribute('data-org-name');
                const currentOrgId = window.currentOrgId;
                const currentUrlName = window.currentUrlName;

                // Don't do anything if clicking on the current organization
                if (orgId === currentOrgId) {
                    switcherDropdown.classList.add('hidden');
                    switcherChevron.classList.remove('rotate-180');
                    return;
                }

                // Get the new URL
                const newUrl = getOrganizationUrl(orgId, currentUrlName);

                // Update the current org name in the button (optimistic update)
                const currentOrgNameElement = document.getElementById('current-org-name');
                if (currentOrgNameElement) {
                    currentOrgNameElement.textContent = orgName;
                }

                // Redirect to the new organization's dashboard
                window.location.href = newUrl;
            });
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initOrganizationSwitcher);
    } else {
        initOrganizationSwitcher();
    }
})();

