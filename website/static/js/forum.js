// HTML escape utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}   
// Forum dynamic filtering functionality
function updateDiscussionList(posts) {
    const discussionList = document.querySelector('ul.space-y-4');
    if (!discussionList) return;

    if (posts.length === 0) {
        discussionList.innerHTML = `
            <li class="bg-white rounded-lg shadow-sm p-6 text-center text-gray-600">
                <p>No discussions found in this category.</p>
            </li>
        `;
        return;
    }

    let html = '';
    posts.forEach(post => {
        const statusClass = getStatusClass(post.status);
        const isPinned = post.is_pinned ? 'border-2 border-[#e74c3c]' : '';
        
        html += `
            <li class="bg-white rounded-lg shadow-sm overflow-hidden ${isPinned}">
                <div class="p-6 border-b border-gray-100">
                    <h2 class="text-xl font-semibold text-gray-800 mb-2">${escapeHtml(post.title)}</h2>
                    <div class="flex flex-wrap gap-4 text-sm text-gray-600">
                        <span class="flex items-center gap-1">
                            <i class="fas fa-user"></i>
                            ${escapeHtml(post.user)}
                        </span>
                        <span class="flex items-center gap-1">
                            <i class="fas fa-clock"></i>
                            ${formatTimeAgo(post.created)}
                        </span>
                        <span class="px-3 py-1 rounded-full text-sm font-medium ${statusClass}">
                            ${escapeHtml(post.status_display)}
                        </span>
                        ${post.category ? `
                            <span class="flex items-center gap-1">
                                <i class="fas fa-tag"></i>
                                ${escapeHtml(post.category)}
                            </span>
                        ` : ''}
                    </div>
                </div>
                <div class="p-6 text-gray-700">
                    <p>${escapeHtml(post.description)}</p>
                </div>
                <div class="flex justify-between items-center px-6 py-4 bg-gray-50 border-t border-gray-100">
                    <div class="flex gap-2">
                        <button type="button"
                                class="flex items-center gap-2 px-4 py-2 rounded-md bg-gray-100 hover:bg-gray-200 transition-colors duration-200"
                                data-vote-type="up"
                                data-suggestion-id="${post.id}">
                            <i class="fas fa-arrow-up"></i>
                            <span class="font-medium">${post.up_votes}</span>
                        </button>
                        <button type="button"
                                class="flex items-center gap-2 px-4 py-2 rounded-md bg-gray-100 hover:bg-gray-200 transition-colors duration-200"
                                data-vote-type="down"
                                data-suggestion-id="${post.id}">
                            <i class="fas fa-arrow-down"></i>
                            <span class="font-medium">${post.down_votes}</span>
                        </button>
                    </div>
                    <div class="flex items-center gap-2 text-gray-600">
                        <i class="fas fa-comments"></i>
                        ${post.comments_count} Comments
                    </div>
                </div>
                <div class="border-t border-gray-100 p-6" id="comments-${post.id}">
                    <form class="mb-6" onsubmit="submitComment(event, ${post.id})">
                        <textarea class="w-full px-4 py-3 border border-gray-200 rounded-md mb-2 focus:outline-none focus:ring-2 focus:ring-[#e74c3c] focus:border-transparent"
                                  placeholder="Add a comment..."
                                  required></textarea>
                        <button type="submit"
                                class="bg-[#e74c3c] text-white px-6 py-2 rounded-md font-medium hover:bg-[#c0392b] transition-colors duration-200">
                            Post Comment
                        </button>
                    </form>
                </div>
            </li>
        `;
    });
    
    discussionList.innerHTML = html;
    
    // Re-initialize voting for new content
    initializeVoting();
}

function getStatusClass(status) {
    switch(status) {
        case 'open': return 'bg-teal-50 text-teal-600';
        case 'in_progress': return 'bg-blue-50 text-blue-600';
        case 'completed': return 'bg-green-50 text-green-600';
        default: return 'bg-red-50 text-red-600';
    }
}

function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
    return `${Math.floor(diffInSeconds / 86400)} days ago`;
}

function updateSidebarHighlight(categoryId) {
    // Remove active class from all sidebar items
    document.querySelectorAll('.sidebar-category-item').forEach(item => {
        item.classList.remove('bg-[#e74c3c]', 'text-white');
        item.classList.add('hover:bg-red-50');
        
        const span = item.querySelector('span:last-child');
        if (span) {
            span.classList.remove('bg-white', 'text-[#e74c3c]');
            span.classList.add('bg-orange-100', 'text-[#e74c3c]');
        }
    });
    
    // Add active class to selected item
    const selectedItem = document.querySelector(`[data-category-id="${categoryId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('bg-[#e74c3c]', 'text-white');
        selectedItem.classList.remove('hover:bg-red-50');
        
        const span = selectedItem.querySelector('span:last-child');
        if (span) {
            span.classList.add('bg-white', 'text-[#e74c3c]');
            span.classList.remove('bg-orange-100');
        }
    }
}

function filterByCategory(categoryId) {
    const params = new URLSearchParams();
    if (categoryId) params.append('category', categoryId);

    const discussionList = document.querySelector('ul.space-y-4');
    if (discussionList) {
        discussionList.innerHTML = '<li class="text-center p-6">Loading...</li>';
    }

    fetch(`/forum/filter/?${params.toString()}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load posts');
            return response.json();
        })
        .then(data => {
            updateDiscussionList(data.posts);
            updateSidebarHighlight(categoryId);
        })
        .catch(err => {
            console.error('Error loading filtered posts:', err);
            if (discussionList) {
                discussionList.innerHTML = `
                    <li class="bg-red-50 text-red-600 rounded-lg p-6 text-center">
                        Failed to load discussions. Please try again.
                    </li>
                `;
            }
        });
}
