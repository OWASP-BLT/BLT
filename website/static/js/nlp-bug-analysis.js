/**
 * NLP Bug Analysis Integration
 * Provides real-time AI-powered suggestions for bug reports
 */

(function() {
    'use strict';

    // Debounce function to limit API calls
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Get CSRF token for POST requests
    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    // Show loading indicator
    function showAnalyzing() {
        const container = document.getElementById('nlp-suggestions');
        if (container) {
            container.innerHTML = `
                <div class="bg-blue-50 dark:bg-blue-900 p-3 rounded-lg border border-blue-200 dark:border-blue-700">
                    <div class="flex items-center">
                        <i class="fa fa-spinner fa-spin mr-2"></i>
                        <span class="text-sm">Analyzing bug report with AI...</span>
                    </div>
                </div>
            `;
            container.classList.remove('hidden');
        }
    }

    // Display suggestions from AI analysis
    function displaySuggestions(analysis) {
        const container = document.getElementById('nlp-suggestions');
        if (!container) return;

        const categoryNames = {
            '0': 'General',
            '1': 'Number Error',
            '2': 'Functional',
            '3': 'Performance',
            '4': 'Security',
            '5': 'Typo',
            '6': 'Design',
            '7': 'Server Down',
            '8': 'Trademark Squatting'
        };

        const severityColors = {
            'low': 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900 dark:border-green-700 dark:text-green-300',
            'medium': 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900 dark:border-yellow-700 dark:text-yellow-300',
            'high': 'bg-orange-50 border-orange-200 text-orange-800 dark:bg-orange-900 dark:border-orange-700 dark:text-orange-300',
            'critical': 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900 dark:border-red-700 dark:text-red-300'
        };

        const suggestedCategory = analysis.suggested_category;
        const categoryName = categoryNames[suggestedCategory] || 'General';
        const severityClass = severityColors[analysis.severity] || severityColors['medium'];

        let html = `
            <div class="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                <div class="flex items-center mb-3">
                    <i class="fa fa-lightbulb-o text-yellow-500 mr-2"></i>
                    <h4 class="font-semibold text-gray-900 dark:text-white">AI Suggestions</h4>
                </div>
                
                <div class="space-y-3">
                    <!-- Suggested Category -->
                    <div>
                        <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Suggested Category:</label>
                        <div class="mt-1">
                            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                                ${categoryName}
                            </span>
                            <button type="button" 
                                    onclick="applySuggestedCategory('${suggestedCategory}')"
                                    class="ml-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">
                                Apply
                            </button>
                        </div>
                    </div>

                    <!-- Severity -->
                    <div>
                        <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Severity:</label>
                        <div class="mt-1">
                            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${severityClass}">
                                ${analysis.severity.toUpperCase()}
                            </span>
                        </div>
                    </div>

                    <!-- Tags -->
                    ${analysis.tags && analysis.tags.length > 0 ? `
                        <div>
                            <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Suggested Tags:</label>
                            <div class="mt-1 flex flex-wrap gap-2">
                                ${analysis.tags.map(tag => `
                                    <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                                        ${tag}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Enhanced Description -->
                    ${analysis.enhanced_description ? `
                        <div>
                            <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Enhanced Description:</label>
                            <div class="mt-1 text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 p-3 rounded">
                                ${analysis.enhanced_description}
                            </div>
                        </div>
                    ` : ''}
                </div>

                <button type="button" 
                        onclick="hideSuggestions()"
                        class="mt-3 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                    <i class="fa fa-times mr-1"></i> Dismiss
                </button>
            </div>
        `;

        container.innerHTML = html;
        container.classList.remove('hidden');
    }

    // Show error message
    function showError(message) {
        const container = document.getElementById('nlp-suggestions');
        if (container) {
            container.innerHTML = `
                <div class="bg-red-50 dark:bg-red-900 p-3 rounded-lg border border-red-200 dark:border-red-700">
                    <div class="flex items-center">
                        <i class="fa fa-exclamation-triangle text-red-600 dark:text-red-400 mr-2"></i>
                        <span class="text-sm text-red-800 dark:text-red-300">${message}</span>
                    </div>
                </div>
            `;
            // Auto-hide error after 5 seconds
            setTimeout(() => {
                container.classList.add('hidden');
            }, 5000);
        }
    }

    // Call the bug analysis API
    async function analyzeBug() {
        const descriptionField = document.querySelector('[name="description"]');
        const urlField = document.querySelector('[name="url"]');
        
        if (!descriptionField || !descriptionField.value.trim()) {
            return;
        }

        const description = descriptionField.value.trim();
        const url = urlField ? urlField.value.trim() : '';

        // Don't analyze very short descriptions
        if (description.length < 20) {
            return;
        }

        showAnalyzing();

        try {
            const formData = new FormData();
            formData.append('description', description);
            formData.append('url', url);
            formData.append('csrfmiddlewaretoken', getCsrfToken());

            const response = await fetch('/get-bug-analysis/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                }
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            const data = await response.json();
            
            if (data.success) {
                displaySuggestions(data);
            } else {
                showError(data.error || 'Unable to analyze bug report');
            }
        } catch (error) {
            console.error('Error analyzing bug:', error);
            showError('Unable to get AI suggestions. Please try again.');
        }
    }

    // Global function to apply suggested category
    window.applySuggestedCategory = function(category) {
        const selectField = document.querySelector('[name="label"]');
        if (selectField) {
            selectField.value = category;
            // Highlight the field briefly
            selectField.classList.add('ring-2', 'ring-green-500');
            setTimeout(() => {
                selectField.classList.remove('ring-2', 'ring-green-500');
            }, 1000);
        }
    };

    // Global function to hide suggestions
    window.hideSuggestions = function() {
        const container = document.getElementById('nlp-suggestions');
        if (container) {
            container.classList.add('hidden');
        }
    };

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        const descriptionField = document.querySelector('[name="description"]');
        
        if (descriptionField) {
            const formGroup = descriptionField.closest('.form-group');
            
            // Add suggestions container if it doesn't exist
            if (!document.getElementById('nlp-suggestions') && formGroup) {
                const container = document.createElement('div');
                container.id = 'nlp-suggestions';
                container.className = 'hidden mt-4';
                // Use insertAdjacentElement instead of .after()
                formGroup.insertAdjacentElement('afterend', container);
            }

            // Analyze when user stops typing (debounced)
            const debouncedAnalyze = debounce(analyzeBug, 2000);
            descriptionField.addEventListener('input', debouncedAnalyze);

            // Add a button to manually trigger analysis
            if (formGroup) {
                const buttonContainer = document.createElement('div');
                buttonContainer.className = 'mt-2';
                buttonContainer.innerHTML = `
                    <button type="button" 
                            id="analyze-bug-btn"
                            class="inline-flex items-center px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">
                        <i class="fa fa-magic mr-2"></i>
                        Get AI Suggestions
                    </button>
                `;
                formGroup.appendChild(buttonContainer);

                const analyzeBtn = document.getElementById('analyze-bug-btn');
                if (analyzeBtn) {
                    analyzeBtn.addEventListener('click', analyzeBug);
                }
            }
        }
    });
})();
