/**
 * Tag Autocomplete Component
 * Provides autocomplete functionality for tag selection with visual styling
 */

class TagAutocomplete {
    constructor(options) {
        this.options = {
            inputSelector: '#tag-input',
            containerSelector: '#tag-container',
            suggestionsSelector: '#tag-suggestions',
            selectedTagsSelector: '#selected-tags',
            apiUrl: '/api/tags/autocomplete/',
            maxTags: 10,
            minQueryLength: 2,
            ...options
        };
        
        this.selectedTags = new Set();
        this.init();
    }
    
    init() {
        this.input = document.querySelector(this.options.inputSelector);
        this.container = document.querySelector(this.options.containerSelector);
        this.suggestions = document.querySelector(this.options.suggestionsSelector);
        this.selectedTagsContainer = document.querySelector(this.options.selectedTagsSelector);
        
        if (!this.input) return;
        
        this.bindEvents();
        this.loadExistingTags();
    }
    
    bindEvents() {
        // Input events
        this.input.addEventListener('input', this.debounce(this.handleInput.bind(this), 300));
        this.input.addEventListener('keydown', this.handleKeyDown.bind(this));
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        
        // Document click to hide suggestions
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.hideSuggestions();
            }
        });
    }
    
    loadExistingTags() {
        // Load existing tags from hidden inputs or data attributes
        const existingTags = this.container.dataset.existingTags;
        if (existingTags) {
            try {
                const tags = JSON.parse(existingTags);
                tags.forEach(tag => this.addTag(tag));
            } catch (e) {
                console.warn('Failed to parse existing tags:', e);
            }
        }
    }
    
    handleInput(e) {
        const query = e.target.value.trim();
        
        if (query.length < this.options.minQueryLength) {
            this.hideSuggestions();
            return;
        }
        
        this.fetchSuggestions(query);
    }
    
    handleKeyDown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const activeSuggestion = this.suggestions.querySelector('.active');
            if (activeSuggestion) {
                this.selectTag(JSON.parse(activeSuggestion.dataset.tag));
            } else {
                // Create new tag if input has value
                const query = this.input.value.trim();
                if (query.length >= 2) {
                    this.createNewTag(query);
                }
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.navigateSuggestions('down');
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.navigateSuggestions('up');
        } else if (e.key === 'Escape') {
            this.hideSuggestions();
        }
    }
    
    handleFocus(e) {
        if (this.input.value.length >= this.options.minQueryLength) {
            this.fetchSuggestions(this.input.value);
        }
    }
    
    async fetchSuggestions(query) {
        try {
            const response = await fetch(`${this.options.apiUrl}?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.displaySuggestions(data.results);
        } catch (error) {
            console.error('Failed to fetch tag suggestions:', error);
        }
    }
    
    displaySuggestions(tags) {
        if (!tags.length) {
            this.hideSuggestions();
            return;
        }
        
        const html = tags
            .filter(tag => !this.selectedTags.has(tag.id))
            .map(tag => `
                <div class="tag-suggestion p-3 cursor-pointer hover:bg-gray-100 border-b border-gray-200 last:border-b-0" 
                     data-tag='${JSON.stringify(tag)}'>
                    <div class="flex items-center">
                        <div class="w-3 h-3 rounded border border-gray-300 mr-3" 
                             style="background-color: ${tag.color};"></div>
                        <div class="flex-1">
                            <div class="font-medium text-gray-900">${this.escapeHtml(tag.name)}</div>
                            <div class="text-sm text-gray-500">${this.escapeHtml(tag.category)}</div>
                        </div>
                        ${tag.icon ? `<i class="${tag.icon} text-gray-400"></i>` : ''}
                    </div>
                </div>
            `).join('');
        
        this.suggestions.innerHTML = html;
        this.suggestions.classList.remove('hidden');
        
        // Bind click events
        this.suggestions.querySelectorAll('.tag-suggestion').forEach(suggestion => {
            suggestion.addEventListener('click', () => {
                const tag = JSON.parse(suggestion.dataset.tag);
                this.selectTag(tag);
            });
        });
    }
    
    navigateSuggestions(direction) {
        const suggestions = this.suggestions.querySelectorAll('.tag-suggestion');
        const current = this.suggestions.querySelector('.active');
        let index = -1;
        
        if (current) {
            index = Array.from(suggestions).indexOf(current);
            current.classList.remove('active', 'bg-gray-100');
        }
        
        if (direction === 'down') {
            index = index + 1 >= suggestions.length ? 0 : index + 1;
        } else {
            index = index <= 0 ? suggestions.length - 1 : index - 1;
        }
        
        if (suggestions[index]) {
            suggestions[index].classList.add('active', 'bg-gray-100');
        }
    }
    
    selectTag(tag) {
        this.addTag(tag);
        this.input.value = '';
        this.hideSuggestions();
    }
    
    addTag(tag) {
        if (this.selectedTags.has(tag.id) || this.selectedTags.size >= this.options.maxTags) {
            return;
        }
        
        this.selectedTags.add(tag.id);
        this.renderSelectedTags();
        
        // Create hidden input for form submission
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = 'tags';
        hiddenInput.value = tag.id;
        hiddenInput.id = `tag-${tag.id}`;
        this.container.appendChild(hiddenInput);
        
        // Trigger custom event
        this.container.dispatchEvent(new CustomEvent('tagAdded', { detail: tag }));
    }
    
    removeTag(tagId) {
        this.selectedTags.delete(tagId);
        this.renderSelectedTags();
        
        // Remove hidden input
        const hiddenInput = document.getElementById(`tag-${tagId}`);
        if (hiddenInput) {
            hiddenInput.remove();
        }
        
        // Trigger custom event
        this.container.dispatchEvent(new CustomEvent('tagRemoved', { detail: { id: tagId } }));
    }
    
    createNewTag(name) {
        // This would typically require an API call to create a new tag
        // For now, we'll just ignore new tag creation to keep it simple
        console.log('New tag creation not implemented:', name);
        this.input.value = '';
    }
    
    renderSelectedTags() {
        if (!this.selectedTagsContainer) return;
        
        // Get tag data for rendering
        const tagData = Array.from(this.selectedTags).map(id => {
            // In a real implementation, you'd store tag data or fetch it
            return { id, name: `Tag ${id}`, color: '#e74c3c' };
        });
        
        const html = tagData.map(tag => `
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white shadow-sm" 
                  style="background-color: ${tag.color};">
                ${this.escapeHtml(tag.name)}
                <button type="button" 
                        class="ml-2 text-white hover:text-gray-200 focus:outline-none"
                        onclick="tagAutocomplete.removeTag(${tag.id})">
                    <i class="fas fa-times"></i>
                </button>
            </span>
        `).join('');
        
        this.selectedTagsContainer.innerHTML = html;
    }
    
    hideSuggestions() {
        this.suggestions.classList.add('hidden');
        this.suggestions.innerHTML = '';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    debounce(func, wait) {
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
}

// Initialize tag autocomplete when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('#tag-input')) {
        window.tagAutocomplete = new TagAutocomplete();
    }
});