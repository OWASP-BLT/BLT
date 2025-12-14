/**
 * Blog functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    // Search functionality
    const searchInput = document.getElementById('post-search');
    const blogCards = document.querySelectorAll('.blog-card');
    
    if (searchInput && blogCards.length > 0) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            
            blogCards.forEach(card => {
                const title = card.querySelector('h2').textContent.toLowerCase();
                const authorElement = card.querySelector('.text-white.text-sm.font-medium');
                const author = authorElement ? authorElement.textContent.toLowerCase() : '';
                
                if (title.includes(searchTerm) || author.includes(searchTerm)) {
                    card.classList.remove('hidden');
                    card.classList.add('block');
                } else {
                    card.classList.remove('block');
                    card.classList.add('hidden');
                }
            });
            
            checkEmptyState();
        });
    }
    
    function checkEmptyState() {
        const visibleCards = document.querySelectorAll('.blog-card:not(.hidden)');
        const grid = document.querySelector('.blog-grid');
        const existingEmptyState = document.querySelector('.empty-state-message');
        
        if (visibleCards.length === 0 && !existingEmptyState && searchInput.value.trim() !== '') {
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-state-message col-span-full flex flex-col items-center justify-center py-16 text-center';
            emptyState.innerHTML = `
                <svg class="w-16 h-16 text-red-500 opacity-50 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <h2 class="text-xl font-semibold text-gray-700 mb-2">No matching posts found</h2>
                <p class="text-gray-500 max-w-md">Try adjusting your search criteria or browse all posts below.</p>
            `;
            grid.appendChild(emptyState);
        } else if ((visibleCards.length > 0 || searchInput.value.trim() === '') && existingEmptyState) {
            existingEmptyState.remove();
        }
    }

    // Style blog content links to be blue
    const blogContent = document.querySelector('.blog-content');
    if (blogContent) {
        const links = blogContent.querySelectorAll('a');
        links.forEach(link => {
            // Apply blue styling to all links in blog content
            link.classList.add('text-blue-600', 'hover:text-blue-800', 'hover:underline');
            link.style.color = '#2563eb'; // Ensures the color is applied even if CSS classes don't load
            
            // Add hover event listeners for better control
            link.addEventListener('mouseenter', function() {
                this.style.color = '#1d4ed8';
                this.style.textDecoration = 'underline';
            });
            
            link.addEventListener('mouseleave', function() {
                this.style.color = '#2563eb';
                this.style.textDecoration = 'none';
            });
        });
    }

    // Smooth scroll to comments
    const commentLinks = document.querySelectorAll('[href="#comments"]');
    commentLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const commentsSection = document.getElementById('comment_root');
            if (commentsSection) {
                commentsSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Blog card hover effects
    const cards = document.querySelectorAll('.blog-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('transform', 'scale-105');
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('transform', 'scale-105');
        });
    });
});
