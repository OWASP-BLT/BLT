document.addEventListener('DOMContentLoaded', function() {
    const timeInput = document.querySelector('input[type="time"]');
    if (timeInput) {
        timeInput.classList.add(
            'block', 'w-full', 'pl-10', 'pr-3', 'py-2', 
            'border', 'border-gray-300', 'rounded-lg',
            'bg-white', 'text-gray-700', 'focus:outline-none',
            'transition', 'duration-150', 'ease-in-out', 'select-none',
            'outline-none'
        );
        
        if (!timeInput.value) {
            const now = new Date();
            const hours = now.getHours().toString().padStart(2, '0');
            const minutes = now.getMinutes().toString().padStart(2, '0');
            timeInput.value = `${hours}:${minutes}`;
        }
    }
    
    const timezoneSelect = document.querySelector('select[name="timezone"]');
    if (timezoneSelect) {
        timezoneSelect.classList.add(
            'block', 'w-full', 'pl-10', 'pr-3', 'py-2',
            'border', 'border-gray-300', 'rounded-lg',
            'bg-white', 'text-gray-700', 'focus:outline-none',
            'transition', 'duration-150', 'ease-in-out',
            'appearance-none', 'select-none',
            'outline-none'
        );
        
        const selectWrapper = timezoneSelect.closest('.timezone-select-wrapper');
        if (selectWrapper) {
            const arrowSvg = document.createElement('div');
            arrowSvg.classList.add('pointer-events-none', 'absolute', 'inset-y-0', 'right-0', 'flex', 'items-center', 'px-2', 'text-gray-500');
            arrowSvg.innerHTML = `
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                </svg>
            `;
            selectWrapper.appendChild(arrowSvg);
            selectWrapper.classList.add('relative');
        }
    }
    
    const checkbox = document.querySelector('input[type="checkbox"]');
    if (checkbox) {
        checkbox.classList.add(
            'peer', 'sr-only'
        );
    }
}); 
