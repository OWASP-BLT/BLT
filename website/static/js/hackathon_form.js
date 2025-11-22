/**
 * Hackathon Form JavaScript
 * Handles dynamic repository loading and form enhancements
 */

$(document).ready(function() {
    // Function to fetch repositories for an organization
    function fetchRepositories(organizationId) {
        if (!organizationId) {
            $('#repositories-loading').hide();
            $('#no-repositories-message').hide();
            $('#id_repositories').empty();
            return;
        }

        $('#repositories-loading').show();
        $('#no-repositories-message').hide();
        $('#id_repositories').empty();

        $.ajax({
            url: `/api/v1/organizations/${organizationId}/repositories/`,
            method: 'GET',
            success: function(data) {
                $('#repositories-loading').hide();
                
                if (data.length === 0) {
                    $('#no-repositories-message').show();
                } else {
                    $('#no-repositories-message').hide();
                    
                    // Add repositories to select
                    data.forEach(function(repo) {
                        let option = new Option(repo.name, repo.id, false, false);
                        $('#id_repositories').append(option);
                    });
                    
                    // If editing, restore selected repositories
                    if (window.selectedRepositories && window.selectedRepositories.length > 0) {
                        $('#id_repositories').val(window.selectedRepositories);
                    }
                }
            },
            error: function() {
                $('#repositories-loading').hide();
                $('#no-repositories-message').show().text('Error loading repositories. Please try again.');
            }
        });
    }

    // Listen for changes on the organization select
    $('#id_organization').change(function() {
        let organizationId = $(this).val();
        fetchRepositories(organizationId);
    });

    // Initial load of repositories if organization is selected
    let initialOrganizationId = $('#id_organization').val();
    if (initialOrganizationId) {
        fetchRepositories(initialOrganizationId);
    }

    // Handle form submission
    $('form').on('submit', function(e) {
        let selectedRepos = $('#id_repositories').val();
        if (selectedRepos && selectedRepos.length > 0) {
            // Ensure all selected values are valid
            let validRepos = [];
            $('#id_repositories option').each(function() {
                if (selectedRepos.includes($(this).val())) {
                    validRepos.push($(this).val());
                }
            });
            $('#id_repositories').val(validRepos);
        }
    });

    // Add character counter for text areas
    $('textarea').each(function() {
        const maxLength = $(this).attr('maxlength');
        if (maxLength) {
            const counterId = $(this).attr('id') + '_counter';
            $(this).after(`<div id="${counterId}" class="text-sm text-gray-500 mt-1"></div>`);
            
            const updateCounter = () => {
                const remaining = maxLength - $(this).val().length;
                $(`#${counterId}`).text(`${remaining} characters remaining`);
            };
            
            $(this).on('input', updateCounter);
            updateCounter();
        }
    });
});
