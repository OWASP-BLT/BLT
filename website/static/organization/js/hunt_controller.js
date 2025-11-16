// Hunt Controller - Fixed Version with Better Error Handling
(function() {
    'use strict';
    
    console.log('[Hunt Controller] Script loading...');
    
    // Add escapeHTML function to prevent XSS attacks
    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    
    // Global variables
let prize_array = [];
    let list_prize_container = null;
    
    // Main functions
    function add_prize() {
        console.log('[add_prize] Function called');
        
        try {
            // Initialize list_prize_container if not already done
            if (!list_prize_container) {
                list_prize_container = document.getElementById("list-prize-container");
                if (!list_prize_container) {
                    console.error('[add_prize] Could not find list-prize-container element');
                    alert('Error: Prize container not found. Please refresh the page.');
                    return;
                }
            }
            
            // Get form elements
            const elements = {
                prize_name: document.getElementById("prize_name"),
                cash_value: document.getElementById("cash_value"),
                number_of_winning_projects: document.getElementById("number_of_winning_projects"),
                every_valid_submissions: document.getElementById("every_valid_submissions"),
                prize_description: document.getElementById("prize_description"),
                paid_in_cryptocurrency: document.getElementById("paid_in_cryptocurrency")
            };
            
            // Check if all elements exist
            for (const [key, element] of Object.entries(elements)) {
                if (!element) {
                    console.error(`[add_prize] Could not find element: ${key}`);
                    alert(`Error: Form element '${key}' not found. Please refresh the page.`);
                    return;
                }
            }
            
            // Set default value for number_of_winning_projects if empty
            if (!elements.number_of_winning_projects.value || elements.number_of_winning_projects.value === "") {
                elements.number_of_winning_projects.value = 1;
            }
            
            // Validate inputs
            if (elements.prize_name.value.trim() === "") {
                alert("Please enter a prize name");
                elements.prize_name.focus();
                return;
            }
            
            if (elements.cash_value.value <= 0) {
                alert("Please enter a valid cash value greater than 0");
                elements.cash_value.focus();
                return;
            }
            
            if (elements.number_of_winning_projects.value <= 0) {
                alert("Number of winning projects must be at least 1");
                elements.number_of_winning_projects.focus();
        return;
    }

            // Create prize data object
            const prize_data = {
                id: `prize_${Date.now()}_${Math.random().toString(36).slice(2,8)}`,
                prize_name: elements.prize_name.value.trim(),
                cash_value: Number(elements.cash_value.value),
                number_of_winning_projects: Number(elements.number_of_winning_projects.value),
                every_valid_submissions: elements.every_valid_submissions.checked,
                prize_description: elements.prize_description.value.trim(),
                paid_in_cryptocurrency: elements.paid_in_cryptocurrency.checked,
                organization_id: window.organizationId || null
            };
            
            console.log('[add_prize] Prize data:', prize_data);
            
            // Add to array
            prize_array.push(prize_data);
            
            // Create prize display element
            createPrizeElement(prize_data);
            
            // Clear form
            elements.prize_name.value = "";
            elements.cash_value.value = "";
            elements.number_of_winning_projects.value = 1;
            elements.every_valid_submissions.checked = false;
            elements.prize_description.value = "";
            elements.paid_in_cryptocurrency.checked = false;
            
            // Re-enable number_of_winning_projects if it was disabled
            if (elements.number_of_winning_projects.disabled) {
                elements.number_of_winning_projects.disabled = false;
                elements.number_of_winning_projects.style.display = "block";
            }
            
            alert("Prize added successfully!");
            console.log('[add_prize] Prize added successfully. Total prizes:', prize_array.length);
            
        } catch (error) {
            console.error('[add_prize] Error:', error);
            alert('An error occurred while adding the prize. Please check the console for details.');
        }
    }
    
    function createPrizeElement(prize_data) {
        const prize_name_sanitized = prize_data.prize_name.trim().length > 12 
            ? prize_data.prize_name.trim().substring(0, 12) + '...' 
            : prize_data.prize_name.trim();
        let prize_description_sanitized = prize_data.prize_description.trim().length > 60 
            ? prize_data.prize_description.trim().substring(0, 60) + '...' 
            : prize_data.prize_description.trim();
        let sanitizedNumberOfWinningProjects = Number(prize_data.number_of_winning_projects);
        
        if (prize_data.every_valid_submissions) {
        sanitizedNumberOfWinningProjects = "All Valid Submissions";
    }
        
        if (!prize_description_sanitized || prize_description_sanitized.trim() === "") {
            prize_description_sanitized = "No description provided";
        }
        
        // Create container
const prizeContainer = document.createElement('div');
prizeContainer.id = `prize-container-${prize_data.id}`;
        prizeContainer.classList.add(
            "bg-white", "border", "border-gray-200", "rounded-xl", "shadow-sm", 
            "hover:shadow-md", "transition-all", "duration-200", "p-6", "w-80", 
            "mr-4", "mb-4", "mt-6", "relative", "group"
        );
        
        // Create header with remove and edit buttons
        const headerDiv = document.createElement('div');
        headerDiv.classList.add("flex", "justify-between", "items-start", "mb-4");
        
        const titleDiv = document.createElement('div');
        titleDiv.classList.add("flex-1", "pr-2");
        titleDiv.innerHTML = `
            <h3 class="text-lg font-semibold text-gray-900 mb-1">${escapeHTML(prize_name_sanitized)}</h3>
            <div class="flex items-center gap-2">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <i class="fas fa-dollar-sign mr-1"></i>
                    $${escapeHTML(prize_data.cash_value)}
                </span>
                ${prize_data.every_valid_submissions ? 
                    '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"><i class="fas fa-infinity mr-1"></i>All Valid</span>' :
                    `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"><i class="fas fa-trophy mr-1"></i>${sanitizedNumberOfWinningProjects} Winners</span>`
                }
            </div>
        `;
        
        const actionDiv = document.createElement('div');
        actionDiv.classList.add("flex", "gap-1", "opacity-0", "group-hover:opacity-100", "transition-opacity", "duration-200");
        
        // Edit button
        const editBtn = document.createElement('button');
        editBtn.classList.add(
            "p-1.5", "text-gray-400", "hover:text-[#e74c3c]", "hover:bg-red-50", 
            "rounded-md", "transition-all", "duration-150", "text-sm"
        );
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
        editBtn.title = "Edit Prize";
        editBtn.onclick = function(e) { 
            editPrize(e, prize_data.id, prize_data.prize_name, prize_data.cash_value, 
                     prize_data.number_of_winning_projects, prize_data.every_valid_submissions, 
                     prize_data.prize_description, prize_data.organization_id); 
        };
        
        // Remove button
const removeBtn = document.createElement('button');
        removeBtn.classList.add(
            "p-1.5", "text-gray-400", "hover:text-red-600", "hover:bg-red-50", 
            "rounded-md", "transition-all", "duration-150", "text-sm"
        );
        removeBtn.innerHTML = '<i class="fas fa-trash-alt"></i>';
        removeBtn.title = "Delete Prize";
        removeBtn.onclick = function() { 
            if(confirm('Are you sure you want to delete this prize?')) {
                remove_prize(prize_data.id); 
            }
        };
        
        actionDiv.appendChild(editBtn);
        actionDiv.appendChild(removeBtn);
        headerDiv.appendChild(titleDiv);
        headerDiv.appendChild(actionDiv);
        prizeContainer.appendChild(headerDiv);
        
        // Create content body
        const bodyDiv = document.createElement('div');
        bodyDiv.classList.add("space-y-3");
        
        // Description section
        const descDiv = document.createElement('div');
        descDiv.classList.add("text-sm", "text-gray-600", "bg-gray-50", "p-3", "rounded-lg", "border-l-4", "border-[#e74c3c]");
        descDiv.innerHTML = `
            <p class="font-medium text-gray-700 mb-1"><i class="fas fa-align-left mr-1 text-[#e74c3c]"></i>Description</p>
            <p class="leading-relaxed">${escapeHTML(prize_description_sanitized)}</p>
        `;
        
        bodyDiv.appendChild(descDiv);
        prizeContainer.appendChild(bodyDiv);
        
        // Add subtle border animation on hover
        prizeContainer.addEventListener('mouseenter', function() {
            this.style.borderColor = '#e74c3c';
        });
        
        prizeContainer.addEventListener('mouseleave', function() {
            this.style.borderColor = '#e5e7eb';
        });
        
list_prize_container.appendChild(prizeContainer);
}

function remove_prize(prize_id) {
        console.log('[remove_prize] Removing prize:', prize_id);
        
        // Remove from array (mutate in place to keep window.prize_array in sync)
        
        // Remove from array (mutate in place to keep window.prize_array in sync)
       const idx = prize_array.findIndex(prize => prize.id === prize_id);
        if (idx !== -1) {
           prize_array.splice(idx, 1);
       }
        // Remove from DOM
        const prize_container = document.getElementById(`prize-container-${prize_id}`);
        if (prize_container) {
            prize_container.remove();
        }
        
        console.log('[remove_prize] Prize removed. Remaining prizes:', prize_array.length);
    }
    
    function PublishBughunt(is_published) {
        console.log('[PublishBughunt] Function called with is_published:', is_published);
        
        try {
            const bughuntForm = document.getElementById("add_bughunt_form");
            if (!bughuntForm) {
                console.error('[PublishBughunt] Form not found');
                alert('Error: Form not found. Please refresh the page.');
                return;
            }
            
            // Check form validity
            if (!bughuntForm.checkValidity()) {
                bughuntForm.reportValidity();
                return;
            }
            
            // Validate that at least one prize is added
            const existingPrizeCards = document.querySelectorAll('[id^="prize-container-"]').length;
            if (prize_array.length === 0 && existingPrizeCards === 0) {
                alert("Please add at least one prize before publishing!");
                return;
            }
            
            console.log('[PublishBughunt] Validation passed. Prizes to submit:', prize_array);
            
            // Check if CSRF token exists
            const csrfToken = bughuntForm.querySelector('input[name="csrfmiddlewaretoken"]');
            if (!csrfToken) {
                console.error('[PublishBughunt] CSRF token not found in form');
                alert('CSRF token missing. Please refresh the page and try again.');
                return;
            }
            console.log('[PublishBughunt] CSRF token found:', csrfToken.value.substring(0, 10) + '...');
            
            // Create hidden inputs for form submission
        const prizeArrayInput = document.createElement('input');
            prizeArrayInput.type = 'hidden';
        prizeArrayInput.name = 'prizes';
        prizeArrayInput.value = JSON.stringify(prize_array);
        
        const publishHunt = document.createElement('input');
            publishHunt.type = 'hidden';
            publishHunt.name = 'publish_bughunt';
            publishHunt.value = is_published;
            
            // Remove any existing hidden inputs with same names
            const existingPrizes = bughuntForm.querySelector('input[name="prizes"]');
            const existingPublish = bughuntForm.querySelector('input[name="publish_bughunt"]');
            if (existingPrizes) existingPrizes.remove();
            if (existingPublish) existingPublish.remove();
            
            // Add new hidden inputs
        bughuntForm.appendChild(prizeArrayInput);
        bughuntForm.appendChild(publishHunt);

            console.log('[PublishBughunt] Form elements:', bughuntForm.elements.length);
            console.log('[PublishBughunt] Form action:', bughuntForm.action);
            console.log('[PublishBughunt] Form method:', bughuntForm.method);
            console.log('[PublishBughunt] Submitting form...');
        bughuntForm.submit();
            
        } catch (error) {
            console.error('[PublishBughunt] Error:', error);
            alert('An error occurred while submitting the form. Please check the console for details.');
        }
    }
    
    function cancelForm() {
        if (confirm("Are you sure you want to cancel? Your progress will be lost.")) {
            window.history.back();
        }
    }
    
    function displayLogoPreview() {
        // This function is kept for backward compatibility
        // The new template uses previewUploadedImage function
        const fileInput = document.getElementById("logo");
        const previewDiv = document.getElementById("previewLogoDiv");
        
        if (!fileInput || !previewDiv) {
            console.error('[displayLogoPreview] Required elements not found');
            return;
        }

    if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            const reader = new FileReader();

        reader.onload = function(event) {
                const preview = document.createElement("img");
        preview.src = event.target.result;
                preview.style.width = "100%";
                preview.style.height = "100%";
                preview.style.objectFit = "cover";
        previewDiv.innerHTML = "";
        previewDiv.appendChild(preview);
        };

        reader.readAsDataURL(file);
    } else {
        previewDiv.innerHTML = "";
    }
}


    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Initialize event listeners when DOM is ready
    function initializeEventListeners() {
        console.log('[initializeEventListeners] Setting up event listeners...');
        
        const valid_s = document.getElementById("every_valid_submissions");
        const winning_projects = document.getElementById("number_of_winning_projects");
        
        if (valid_s && winning_projects) {
            valid_s.addEventListener('click', function() {
                winning_projects.value = 1;
                if (valid_s.checked) {
                    winning_projects.disabled = true;
                    winning_projects.style.display = "none";
                } else {
                    winning_projects.disabled = false;
                    winning_projects.style.display = "block";
                }
            });
            console.log('[initializeEventListeners] Checkbox listener added');
        }
    }
    
    // Additional functions for edit mode
function removePrize(event, prizeId, organizationId) {
    event.preventDefault();
    if (!confirm("Are you sure you want to delete this prize?")) {
        return;
    }

        // Show loading indicator
    let prizeContainer = document.getElementById(`prize-container-${prizeId}`);
    let loadingIndicator = document.createElement('div');
    loadingIndicator.innerText = "Loading...";
    prizeContainer.appendChild(loadingIndicator);

        // Make AJAX call to delete the prize
    fetch(`/organization/delete_prize/${prizeId}/${organizationId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
    .then(data => {
        if (data.success) {
            prizeContainer.parentNode.removeChild(prizeContainer);
            alert("Prize deleted successfully!");
        } else {
                alert(data.message || "Failed to delete prize. Please try again.");
        }
    })
    .catch(error => {
        console.error('Error:', error);
            alert("Network error occurred while deleting the prize. Please check your connection and try again.");
        })
        .finally(() => {
            if (loadingIndicator && loadingIndicator.parentNode) {
                loadingIndicator.remove();
            }
    });
}

function editPrize(event, prizeId, prizeName, cashValue, noOfProjects, validSubmissions, description, organizationId) {
        event.preventDefault();
    alert("Edit the prize details in the form above and click the 'Update Prize' button to save changes.");
    document.getElementById('prize_name').value = prizeName;
    document.getElementById('cash_value').value = cashValue;
    document.getElementById('number_of_winning_projects').value = noOfProjects;
        
    if (validSubmissions) {
        document.getElementById('number_of_winning_projects').disabled = true;
        document.getElementById('number_of_winning_projects').style.display = "none";
    }
        
    document.getElementById('prize_description').value = description;
    document.getElementById('every_valid_submissions').checked = validSubmissions ? true : false;
    document.getElementById('add_prize_button').innerText = 'Update Prize';
    const addPrizeButton = document.getElementById('add_prize_button');
    addPrizeButton.onclick = null; // Clear any previous handler
    addPrizeButton.onclick = function() { updatePrize(prizeId, organizationId); };
    document.getElementById('cryptocurrencyDiv').style.display = "none";
}

    function updatePrize(prizeId, organizationId) {
        let prize_name = document.getElementById("prize_name");
        let cash_value = document.getElementById("cash_value");
        let number_of_winning_projects = document.getElementById("number_of_winning_projects");
        let every_valid_submissions = document.getElementById("every_valid_submissions");
        let prize_description = document.getElementById("prize_description");
        
        // Set default value for number_of_winning_projects if empty
        if (!number_of_winning_projects.value || number_of_winning_projects.value === "") {
            number_of_winning_projects.value = 1;
        }
        
        if (prize_name.value.trim() === "" || cash_value.value <= 0 || number_of_winning_projects.value <= 0) {
            alert("Please fill in all fields correctly");
            return;
        }
        
        let prize_data = {
            id: prizeId,
            prize_name: prize_name.value,
            cash_value: cash_value.value,
            number_of_winning_projects: number_of_winning_projects.value,
            every_valid_submissions: every_valid_submissions.checked,
            prize_description: prize_description.value,
            organization_id: organizationId
        };
        
        console.log('[updatePrize] Updating prize:', prize_data);
        
        // Update the prize in the prize_array (client-side only for new bounties)
        const prizeIndex = prize_array.findIndex(p => p.id == prizeId);
        if (prizeIndex !== -1) {
            prize_array[prizeIndex] = prize_data;
            console.log('[updatePrize] Updated prize_array:', prize_array);
        }
        
        // Remove the old prize element and create a new one with updated data
        const oldPrizeContainer = document.getElementById(`prize-container-${prizeId}`);
        if (oldPrizeContainer) {
            oldPrizeContainer.remove();
        }
        
        // Create updated prize element
        createPrizeElement(prize_data);
        
        // Reset the form completely
        prize_name.value = "";
        cash_value.value = "";
        number_of_winning_projects.value = "1";
        every_valid_submissions.checked = false;
        prize_description.value = "";
        
        // Restore number_of_winning_projects input visibility and enabled state
        number_of_winning_projects.disabled = false;
        number_of_winning_projects.style.display = "";
        
        // Reset the "Add Prize" button
        const addPrizeButton = document.getElementById('add_prize_button');
        addPrizeButton.innerText = 'Add Prize';
        addPrizeButton.onclick = add_prize;
        addPrizeButton.disabled = false;
        
        // Show success message
        alert('Prize updated successfully!');
        
        console.log('[updatePrize] Prize updated successfully');
    }
    
     // Image preview functions for logo/banner uploads
     function previewUploadedImage(input, previewId, defaultIconId, removeButtonId) {
         const preview = document.getElementById(previewId);
         const defaultIcon = document.getElementById(defaultIconId);
         const removeButton = document.getElementById(removeButtonId);
         
         // Determine error div based on preview type (logo vs banner)
         const errorDivId = previewId.includes('logo') ? 'logoError' : 'bannerError';
         const errorDiv = document.getElementById(errorDivId);
         
         // Clear any previous errors
         if (errorDiv) {
             errorDiv.style.display = 'none';
             errorDiv.textContent = '';
         }

        if (!preview || !defaultIcon || !removeButton) {
            console.error('One or more required elements not found');
            return;
        }

        if (input.files && input.files[0]) {
            const file = input.files[0];
            
            // Validate file type
            const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
            if (!validTypes.includes(file.type)) {
                if (errorDiv) {
                    errorDiv.textContent = 'Please select a valid image file (JPG, PNG, GIF, or WebP)';
                    errorDiv.style.display = 'block';
                }
                input.value = '';
                return;
            }
            
            // Validate file size (5MB = 5 * 1024 * 1024 bytes)
            const maxSize = 5 * 1024 * 1024;
            if (file.size > maxSize) {
                if (errorDiv) {
                    errorDiv.textContent = 'File size must be less than 5MB';
                    errorDiv.style.display = 'block';
                }
                input.value = '';
                return;
            }

            const reader = new FileReader();
            
            reader.onload = function(e) {
                // Set the image source
                preview.src = e.target.result;
                
                // Use style.display for more reliable showing/hiding
                preview.style.display = 'block';
                defaultIcon.style.display = 'none';
                removeButton.style.display = 'inline-flex';
                
                // Also use classList as backup
                preview.classList.remove('hidden');
                defaultIcon.classList.add('hidden');
                removeButton.classList.remove('hidden');
            }
            
            reader.onerror = function() {
                console.error('Error reading file');
                if (errorDiv) {
                    errorDiv.textContent = 'Error reading the file. Please try again.';
                    errorDiv.style.display = 'block';
                }
                input.value = '';
            }
            
            reader.readAsDataURL(file);
        }
    }

     function removeUploadedImage(inputId, previewId, defaultIconId, removeButtonId) {
         const input = document.getElementById(inputId);
         const preview = document.getElementById(previewId);
         const defaultIcon = document.getElementById(defaultIconId);
         const removeButton = document.getElementById(removeButtonId);
         
         // Determine error div based on input type (logo vs banner)
         const errorDivId = inputId.includes('logo') ? 'logoError' : 'bannerError';
         const errorDiv = document.getElementById(errorDivId);

        if (!input || !preview || !defaultIcon || !removeButton) {
            console.error('One or more required elements not found');
            return;
        }
        
        // Clear the file input and preview
        input.value = '';
        preview.src = '';
        
        // Use style.display for more reliable showing/hiding
        preview.style.display = 'none';
        defaultIcon.style.display = 'flex';
        removeButton.style.display = 'none';
        
        // Also use classList as backup
        preview.classList.add('hidden');
        defaultIcon.classList.remove('hidden');
        removeButton.classList.add('hidden');
        
        // Clear any errors
        if (errorDiv) {
            errorDiv.style.display = 'none';
            errorDiv.textContent = '';
        }
    }
    
    // Expose functions globally

    window.add_prize = add_prize;
    window.PublishBughunt = PublishBughunt;
    window.cancelForm = cancelForm;
    window.displayLogoPreview = displayLogoPreview;
    window.previewUploadedImage = previewUploadedImage;
    window.removeUploadedImage = removeUploadedImage;
    window.remove_prize = remove_prize;
    window.removePrize = removePrize;
    window.editPrize = editPrize;
    window.updatePrize = updatePrize;
    window.escapeHTML = escapeHTML;
    window.prize_array = prize_array;
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeEventListeners);
    } else {
        // DOM is already loaded
        initializeEventListeners();
    }
    
    console.log('[Hunt Controller] Script loaded successfully');
    console.log('[Hunt Controller] Functions available:', {
        add_prize: typeof window.add_prize,
        PublishBughunt: typeof window.PublishBughunt,
        cancelForm: typeof window.cancelForm
    });
    
})();