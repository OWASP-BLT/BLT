

let prize_array = [];
let list_prize_container = document.getElementById("list-prize-container");

function remove_prize_container(){
    let email_container = document.getElementById("email-container");
    let lst_child = email_container.lastElementChild;
    email_container.removeChild(lst_child);
}

function add_prize(){
                
    let prize_name = document.getElementById("prize_name");
    let cash_value = document.getElementById("cash_value");
    let number_of_winning_projects = document.getElementById("number_of_winning_projects");
    let every_valid_submissions = document.getElementById("every_valid_submissions");
    let prize_description = document.getElementById("prize_description");
    let paid_in_cryptocurrency = document.getElementById("paid_in_cryptocurrency");

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
    every_valid_submissions.checked = false;
    prize_description.value = "";
    paid_in_cryptocurrency.checked = false;

    const prize_container_child_html = document.createElement('div');
    const prize_name_sanitized = prize_data.prize_name.trim().substring(0, 8) + '...'; // Sanitize prize_name
    const prize_description_sanitized = prize_data.prize_description.trim().substring(0, 55) + '...'; // Sanitize prize_description
    const sanitizedNumberOfWinningProjects = Number(prize_data.number_of_winning_projects); // Sanitize number_of_winning_projects
    prize_container_child_html.innerHTML = `
            <div class="bg-white rounded-lg shadow-lg p-6 w-72 mr-5">
                <h2 class="text-2xl font-bold mb-4 text-gray-800">${escapeHTML(prize_name_sanitized)}</h2>
                <div class="mb-4">
                    <p class="text-red-500 font-bold">Cash Value (USD)</p>
                    <p class="text-gray-800">$1000</p>
                </div>
                <div class="mb-4">
                    <p class="text-gray-800 font-bold">Number of Winning Projects</p>
                    <p class="text-gray-600">${sanitizedNumberOfWinningProjects}</p>
                </div>
                <div class="mb-4">
                    <p class="text-gray-800 font-bold">Reward Valid Submission</p>
                    <p class="text-gray-600">${prize_data.every_valid_submissions}</p>
                </div>
                <div class="mb-4">
                    <p class="text-red-500 font-bold">Prize Description</p>
                    <p class="text-gray-800">${escapeHTML(prize_description_sanitized)}</p>
                </div>
            </div>
    `;

    list_prize_container.appendChild(prize_container_child_html);
    function escapeHTML(unsafeText) {
        const div = document.createElement('div');
        div.innerText = unsafeText;
        return div.innerHTML;
    }
}

function cancelForm(){
    let deleteForm = document.getElementById("deleteForm");
    let confirmDelete = confirm("Are you sure you want to cancel, your progress would be lost.");
    if (confirmDelete === true){
        deleteForm.submit();
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


