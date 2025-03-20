

let prize_array = [];
let list_prize_container = document.getElementById("list-prize-container");

function add_prize(){
                
    let prize_name = document.getElementById("prize_name");
    let cash_value = document.getElementById("cash_value");
    let number_of_winning_projects = document.getElementById("number_of_winning_projects");
    let every_valid_submissions = document.getElementById("every_valid_submissions");
    let prize_description = document.getElementById("prize_description");
    let paid_in_cryptocurrency = document.getElementById("paid_in_cryptocurrency");

    if (prize_name.value.trim() === "" || cash_value.value <= 0 || number_of_winning_projects.value <= 0){
        alert("Please fill in all fields correctly");
        return;
    }

    let prize_data = {
        id: prize_array.length,
        prize_name: prize_name.value,
        cash_value: cash_value.value,
        number_of_winning_projects: number_of_winning_projects.value,
        every_valid_submissions: every_valid_submissions.checked,
        prize_description: prize_description.value,
        paid_in_cryptocurrency: paid_in_cryptocurrency.checked
    }
    

    prize_array.push(prize_data)
    alert("Prize added successfully");
    
    prize_name.value = "";
    cash_value.value = 0;
    number_of_winning_projects.value = 1;
    if(number_of_winning_projects.disabled){
        number_of_winning_projects.disabled = false;
        number_of_winning_projects.style.display = "block";
    }
    every_valid_submissions.checked = false;
    prize_description.value = "";
    paid_in_cryptocurrency.checked = false;

    const prize_container_child_html = document.createElement('div');
    const prize_name_sanitized = prize_data.prize_name.trim().substring(0, 8) + '...'; // Sanitize prize_name
    let prize_description_sanitized = prize_data.prize_description.trim().substring(0, 55) + '...'; // Sanitize prize_description
    let sanitizedNumberOfWinningProjects = Number(prize_data.number_of_winning_projects); // Sanitize number_of_winning_projects

    // if every_valid_submissions is checked, the number_of_winning_projects will be "all valid submissions"
    if (prize_data.every_valid_submissions){
        sanitizedNumberOfWinningProjects = "All Valid Submissions";
    }
    // if the description is empty, the prize_description will be "No Description"
    if (prize_description_sanitized === "..."){
        prize_description_sanitized = "No Description";
    }
    // Create a container for the prize
const prizeContainer = document.createElement('div');
prizeContainer.id = `prize-container-${prize_data.id}`;
prizeContainer.classList.add("bg-white", "rounded-lg", "shadow-lg", "p-6", "w-72", "mr-5", "relative");

// Create the remove button
const removeBtn = document.createElement('button');
removeBtn.classList.add("absolute", "top-2", "right-2", "text-red-500");
removeBtn.textContent = "x";
removeBtn.addEventListener('click', () => remove_prize(prize_data.id));
prizeContainer.appendChild(removeBtn);

// Create the prize name heading
const heading = document.createElement('h2');
heading.classList.add("text-2xl", "font-bold", "mb-4", "text-gray-800");
heading.textContent = escapeHTML(prize_name_sanitized);
prizeContainer.appendChild(heading);

// Create Cash Value section
const cashDiv = document.createElement('div');
cashDiv.classList.add("mb-4");
const cashLabel = document.createElement('p');
cashLabel.classList.add("text-red-500", "font-bold");
cashLabel.textContent = "Cash Value (USD)";
cashDiv.appendChild(cashLabel);
const cashValue = document.createElement('p');
cashValue.classList.add("text-gray-800");
cashValue.textContent = `$${prize_data.cash_value}`;
cashDiv.appendChild(cashValue);
prizeContainer.appendChild(cashDiv);

// Create Number of Winning Projects section
const projectsDiv = document.createElement('div');
projectsDiv.classList.add("mb-4");
const projectsLabel = document.createElement('p');
projectsLabel.classList.add("text-gray-800", "font-bold");
projectsLabel.textContent = "Number of Winning Projects";
projectsDiv.appendChild(projectsLabel);
const projectsValue = document.createElement('p');
projectsValue.classList.add("text-gray-600");
projectsValue.textContent = sanitizedNumberOfWinningProjects;
projectsDiv.appendChild(projectsValue);
prizeContainer.appendChild(projectsDiv);

// Create Reward All Valid Submission section
const validDiv = document.createElement('div');
validDiv.classList.add("mb-4");
const validLabel = document.createElement('p');
validLabel.classList.add("text-gray-800", "font-bold");
validLabel.textContent = "Reward All Valid Submission";
validDiv.appendChild(validLabel);
const validValue = document.createElement('p');
validValue.classList.add("text-gray-600");
validValue.textContent = prize_data.every_valid_submissions;
validDiv.appendChild(validValue);
prizeContainer.appendChild(validDiv);

// Create Prize Description section
const descDiv = document.createElement('div');
descDiv.classList.add("mb-4");
const descLabel = document.createElement('p');
descLabel.classList.add("text-red-500", "font-bold");
descLabel.textContent = "Prize Description";
descDiv.appendChild(descLabel);
const descValue = document.createElement('p');
descValue.classList.add("text-gray-800");
descValue.textContent = escapeHTML(prize_description_sanitized);
descDiv.appendChild(descValue);
prizeContainer.appendChild(descDiv);

// Append the complete prize container to the list
list_prize_container.appendChild(prizeContainer);


    list_prize_container.appendChild(prize_container_child_html);
    function escapeHTML(unsafeText) {
        const div = document.createElement('div');
        div.innerText = unsafeText;
        return div.innerHTML;
    }
}

function remove_prize(prize_id) {
    let confirmDelete = confirm("Are you sure you want to delete this prize?");
    if (!confirmDelete) {
        return;
    }
    prize_array = prize_array.filter(prize => prize.id !== prize_id);
    let prize_container = document.getElementById(`prize-container-${prize_id}`);
    if (prize_container && prize_container.parentNode) {
        let grandParent = prize_container.parentNode;
        if (grandParent.parentNode) {
            grandParent.parentNode.removeChild(grandParent);
        }
    }
}

function cancelForm(){
    let confirmDelete = confirm("Are you sure you want to cancel, your progress would be lost.");
    if (confirmDelete === true){
        window.history.back();
    }
}

function PublishBughunt(is_published){
    
    const bughuntForm = document.getElementById("add_bughunt_form");

    if (bughuntForm.checkValidity()){
        const prizeArrayInput = document.createElement('input');
        prizeArrayInput.type = 'text';
        prizeArrayInput.name = 'prizes';
        prizeArrayInput.value = JSON.stringify(prize_array);
        
        const publishHunt = document.createElement('input');
        publishHunt.type = "text";
        publishHunt.name = "publish_bughunt";
        publishHunt.value = is_published

        bughuntForm.appendChild(prizeArrayInput);
        bughuntForm.appendChild(publishHunt);

        bughuntForm.submit();
    }

    else{
        bughuntForm.reportValidity();
    }

    

}

function displayLogoPreview() {
    var fileInput = document.getElementById("logo");
    var previewDiv = document.getElementById("previewLogoDiv");

    if (fileInput.files.length > 0) {
        var file = fileInput.files[0];
        var reader = new FileReader();

        reader.onload = function(event) {
        var preview = document.createElement("img");
        preview.src = event.target.result;
        previewDiv.innerHTML = "";
        previewDiv.appendChild(preview);
        };

        reader.readAsDataURL(file);
    } else {
        previewDiv.innerHTML = "";
    }
}

let valid_s = document.getElementById("every_valid_submissions");
let winning_projects = document.getElementById("number_of_winning_projects");
valid_s.addEventListener('click',()=>{
    winning_projects.value = 1;
    if (valid_s.checked) {
        winning_projects.disabled = true;
        winning_projects.style.display = "none";
    } else {
        winning_projects.disabled = false;
        winning_projects.style.display = "block";
    }
})

function displayBannerPreview() {
    var fileInput = document.getElementById("banner");
    var previewDiv = document.getElementById("bannerPreview");

    if (fileInput.files.length > 0) {
        var file = fileInput.files[0];
        var reader = new FileReader();

        reader.onload = function(event) {
            var img = new Image();
            img.src = event.target.result;

            img.onload = function() {
                var canvas = document.createElement("canvas");
                var ctx = canvas.getContext("2d");

                var maxDim = 300;
                var scale = Math.min(maxDim / img.width, maxDim / img.height);

                canvas.width = img.width * scale;
                canvas.height = img.height * scale;

                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

                previewDiv.innerHTML = "";
                previewDiv.style.display = "flex";
                previewDiv.style.justifyContent = "center";
                previewDiv.appendChild(canvas);
            };
        };

        reader.readAsDataURL(file);
    } else {
        previewDiv.innerHTML = "";
    }
}

function removePrize(event, prizeId, organizationId) {
    event.preventDefault();
    if (!confirm("Are you sure you want to delete this prize?")) {
        return;
    }

    // Show loading indicator (you can customize this as needed)
    let prizeContainer = document.getElementById(`prize-container-${prizeId}`);
    let loadingIndicator = document.createElement('div');
    loadingIndicator.innerText = "Loading...";
    prizeContainer.appendChild(loadingIndicator);

    // Make AJAX call to delete the prize with organization_id
    fetch(`/organization/delete_prize/${prizeId}/${organizationId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove the prize from the DOM
            prizeContainer.parentNode.removeChild(prizeContainer);
            alert("Prize deleted successfully!");
        } else {
            alert("Failed to delete prize. Please try again.");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("An error occurred. Please try again.");
    });
}

function editPrize(event, prizeId, prizeName, cashValue, noOfProjects, validSubmissions, description, organizationId) {
    event.preventDefault(); // Prevent the form from submitting
    alert("Edit the prize details in the form above and click the 'Update Prize' button to save changes.");
    document.getElementById('prize_name').value = prizeName;
    document.getElementById('cash_value').value = cashValue;
    document.getElementById('number_of_winning_projects').value = noOfProjects;
    // if every_valid_submissions is true then disable the number_of_winning_projects input field and also hide it
    if (validSubmissions) {
        document.getElementById('number_of_winning_projects').disabled = true;
        document.getElementById('number_of_winning_projects').style.display = "none";
    }
    document.getElementById('prize_description').value = description;
    document.getElementById('every_valid_submissions').checked = validSubmissions ? true : false;
    document.getElementById('add_prize_button').innerText = 'Update Prize';
    document.getElementById('add_prize_button').setAttribute('onclick', `updatePrize(${prizeId}, ${organizationId})`);
    // hive the cryptocurrencyDiv 
    document.getElementById('cryptocurrencyDiv').style.display = "none";
}

function updatePrize(prizeId, organizationId) {
    let prize_name = document.getElementById("prize_name");
    let cash_value = document.getElementById("cash_value");
    let number_of_winning_projects = document.getElementById("number_of_winning_projects");
    let every_valid_submissions = document.getElementById("every_valid_submissions");
    let prize_description = document.getElementById("prize_description");

    if (prize_name.value.trim() === "" || cash_value.value <= 0 || number_of_winning_projects.value <= 0){
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
    }

    // Make AJAX call to update the prize with organization_id
    fetch(`/organization/edit_prize/${prizeId}/${organizationId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(prize_data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the prize in the DOM
            let prizeContainer = document.getElementById(`prize-container-${prizeId}`);
            const paragraph = prizeContainer.querySelectorAll('p');
            prize_data.prize_name = prize_data.prize_name.trim().substring(0, 8) + '...';
            prizeContainer.querySelector('h2').innerText = prize_data.prize_name;
            paragraph[1].innerText = `$${prize_data.cash_value}`;
            if (prize_data.every_valid_submissions){
                prize_data.number_of_winning_projects = "All Valid Submissions";
            }
            paragraph[3].innerText = prize_data.number_of_winning_projects;
            paragraph[5].innerText = prize_data.every_valid_submissions;
            // description slice to 55 characters
            prize_data.prize_description = prize_data.prize_description.trim().substring(0, 55) + '...';
            paragraph[7].innerText = prize_data.prize_description;
            // we should have to update the edit button to update the editPrize function attributes
            prizeContainer.querySelector('#EditPrizeButton').setAttribute('onclick', `editPrize(event, ${prizeId}, '${prize_data.prize_name}', ${prize_data.cash_value}, ${prize_data.number_of_winning_projects}, ${prize_data.every_valid_submissions}, '${prize_data.prize_description}', ${organizationId})`);
            // and then reset the form
            prize_name.value = "";
            cash_value.value = 0;
            number_of_winning_projects.value = 1;
            if(number_of_winning_projects.disabled){
                number_of_winning_projects.disabled = false;
                number_of_winning_projects.style.display = "block";
            }
            every_valid_submissions.checked = false;
            prize_description.value = "";
            document.getElementById('add_prize_button').innerText = 'Add Prize';
            document.getElementById('add_prize_button').setAttribute('onclick', 'add_prize()');
            document.getElementById('cryptocurrencyDiv').style.display = "block";
            alert('Prize updated successfully');
        } else {
            alert("Failed to update prize. Please try again.");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("An error occurred. Please try again.");
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}