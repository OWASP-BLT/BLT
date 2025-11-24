// Anonymous Hunt Form JavaScript
(function() {
    'use strict';
    
    let prizeCount = 0;
    let prizes = new Map();  // Use Map to track prizes by ID

    function updatePrizesInput() {
        // Convert Map to array for JSON serialization
        const prizesArray = Array.from(prizes.values()).filter(prize => prize.prize_name.trim() !== '');
        const prizesInput = document.getElementById('prizes');
        if (prizesInput) {
            prizesInput.value = JSON.stringify(prizesArray);
        }
        updateTotalPayment();
    }

    function updateTotalPayment() {
        const prizesArray = Array.from(prizes.values());
        const total = prizesArray.reduce((sum, prize) => sum + parseInt(prize.cash_value || 0, 10), 0);
        const totalElement = document.getElementById('total-payment');
        if (totalElement) {
            totalElement.textContent = '$' + total;
        }
    }

    function addPrize() {
        prizeCount++;
        const prizeId = `prize-${prizeCount}`;
        
        const prizeHTML = `
            <div id="${prizeId}" class="p-4 border border-gray-200 rounded-md">
                <div class="grid grid-cols-1 gap-4 sm:grid-cols-6">
                    <div class="sm:col-span-3">
                        <label for="${prizeId}-name" class="block text-sm font-medium text-gray-700">Prize Name</label>
                        <input type="text" 
                               id="${prizeId}-name"
                               data-prize-id="${prizeId}" 
                               data-field="prize_name" 
                               placeholder="e.g., First Place" 
                               class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring-[#e74c3c] sm:text-sm px-3 py-2 border" />
                    </div>
                    <div class="sm:col-span-2">
                        <label for="${prizeId}-value" class="block text-sm font-medium text-gray-700">Cash Value ($)</label>
                        <input type="number" 
                               id="${prizeId}-value"
                               data-prize-id="${prizeId}" 
                               data-field="cash_value" 
                               placeholder="500" 
                               min="0" 
                               class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring-[#e74c3c] sm:text-sm px-3 py-2 border" />
                    </div>
                    <div class="sm:col-span-1 flex items-end">
                        <button type="button" 
                                data-prize-id="${prizeId}"
                                class="remove-prize-btn w-full px-3 py-2 text-sm font-medium text-red-600 hover:text-red-800 border border-red-600 rounded-md hover:bg-red-50">
                            Remove
                        </button>
                    </div>
                    <div class="sm:col-span-6">
                        <label for="${prizeId}-description" class="block text-sm font-medium text-gray-700">Description (optional)</label>
                        <textarea id="${prizeId}-description"
                                  data-prize-id="${prizeId}" 
                                  data-field="prize_description" 
                                  rows="2" 
                                  placeholder="Describe the prize criteria..." 
                                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-[#e74c3c] focus:ring-[#e74c3c] sm:text-sm px-3 py-2 border"></textarea>
                    </div>
                </div>
            </div>
        `;
        
        const container = document.getElementById('prizes-container');
        if (container) {
            container.insertAdjacentHTML('beforeend', prizeHTML);
        }
        
        // Initialize prize data in Map
        prizes.set(prizeId, {
            prize_name: '',
            cash_value: 0,
            prize_description: '',
            number_of_winning_projects: 1,
            every_valid_submissions: false,
            paid_in_cryptocurrency: false
        });
        
        // Add event listeners for inputs
        document.querySelectorAll(`[data-prize-id="${prizeId}"]`).forEach(element => {
            if (element.classList.contains('remove-prize-btn')) {
                element.addEventListener('click', function() {
                    removePrize(prizeId);
                });
            } else {
                element.addEventListener('input', function() {
                    const prize = prizes.get(prizeId);
                    if (prize) {
                        prize[this.dataset.field] = this.value;
                        updatePrizesInput();
                    }
                });
            }
        });
        
        updatePrizesInput();
    }

    function removePrize(prizeId) {
        const element = document.getElementById(prizeId);
        if (element) {
            element.remove();
        }
        prizes.delete(prizeId);
        updatePrizesInput();
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        const addPrizeBtn = document.getElementById('add-prize-btn');
        if (addPrizeBtn) {
            addPrizeBtn.addEventListener('click', addPrize);
        }
        
        // Add at least one prize initially
        addPrize();
    });
})();
