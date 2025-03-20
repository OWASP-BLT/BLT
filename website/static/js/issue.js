function renderer(data) {
    $('#text_comment').atwho({
        at: "@",
        data: data
    });
}

window.twttr = (function (d, s, id) {

    var js, fjs = d.getElementsByTagName(s)[0], t = window.twttr || {};
    if (d.getElementById(id)) return t;
    js = d.createElement(s);
    js.id = id;
    js.src = "https://platform.twitter.com/widgets.js";
    fjs.parentNode.insertBefore(js, fjs);
    t._e = [];

    t.ready = function (f) {
        t._e.push(f);
    };
    return t;

}(document, "script", "twitter-wjs"));

(function (d, s, id) {
    var js, fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    js = d.createElement(s);
    js.id = id;
    js.src = "//connect.facebook.net/en_US/sdk.js#xfbml=1&version=v2.7&appId=236647900066394";
    fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));

$(function () {
    var comment_id, old_message;

    new Clipboard('.btn');
    $('.copy-btn').on('click', function () {
        $.notify('Copied!', {style: "custom", className: "success"});
    });

    $(document).on('submit', '#comments', function (e) {
        e.preventDefault();
        if ($('#text_comment').val().trim().length == 0) {
            $('.alert-danger').removeClass("hidden");
            return;
        }
        $('.alert-danger').addClass("hidden");
        $.ajax({
            type: 'POST',
            url: '/issue/comment/add/',
            data: {
                text_comment: $('#text_comment').val().trim(),
                issue_pk: $('#issue_pk').val(),
                csrfmiddlewaretoken: $('#comments input[name=csrfmiddlewaretoken]').val(),
            },
            success: function (data) {
                $('#target_div').html(data);
                $('#text_comment').val('');
            }
        });
    });

    $('body').on('click', '.del_comment', function (e) {
        e.preventDefault();
        if (confirm("Delete this comment?") == true) {
            $.ajax({
                type: 'POST',
                url: "/issue/comment/delete/",
                data: {
                    comment_pk: $(this).attr('name'),
                    issue_pk: $('#issue_pk').val(),
                    csrfmiddlewaretoken: $('#comments input[name=csrfmiddlewaretoken]').val(),
                },
                success: function (data) {
                    $('#target_div').html(data);
                },
            });
        }
    });

    $('body').on('click', '.edit_comment', function (e) {
        e.preventDefault();
        old_message = $(this).parent().next().next().text();
        comment_id = $(this).attr('name');
        $(this).hide();
        $(this).next('.edit_comment').hide();
        $(this).next('.del_comment').hide();
        $(this).parent().next().find('textarea').val(old_message);
        $(this).parent().parent().next().show();
    });

    $(document).on('click', '.edit_form button[type="submit"]', function (e) {
        e.preventDefault();
        var issue_id = $('#issue_pk').val();
        var comment = $(this).prev().find('textarea').val();
        if (comment == '') return;
        $.ajax({
            type: 'GET',
            url: '/issue/' + issue_id + '/comment/edit/',
            data: {
                comment_pk: comment_id,
                text_comment: comment,
                issue_pk: issue_id,
            },
            success: function (data) {
                $('#target_div').html(data);
            }
        });
    });


    $('body').on('click', '.reply_comment', function (e) {
        e.preventDefault();
        comment_id = $(this).attr('name');
        $(this).parent().parent().parent().next().toggle();
    });

    $(document).on('click', '.reply_form button[type="submit"]', function (e) {
        e.preventDefault();
        var parent_id = $(this).val();
        var issue_id = $('#issue_pk').val();
        var comment = $(this).prev().find('textarea').val();
        if (comment == '') return;
        $.ajax({
            type: 'GET',
            url: '/issue/' + issue_id + '/comment/reply/',
            data: {
                comment_pk: comment_id,
                text_comment: comment,
                issue_pk: issue_id,
                parent_id: parent_id,
            },
            success: function (data) {
                $('#target_div').html(data);
            }
        });
    });

    $('body').on('input, keyup', 'textarea', function () {
        var search = $(this).val();
        var data = {search: search};
        $.ajax({
            type: 'GET',
            url: '/comment/autocomplete/',
            data: data,
            dataType: 'jsonp',
            jsonp: 'callback',
            jsonpCallback: 'renderer',
        });
    });


    $(document).on('click', '.cancel-comment-edit', function (e) {
        e.preventDefault();
        $('.edit_form').hide();
        $(this).parent().parent().find('.edit_comment').show();
        $(this).parent().parent().find('.del_comment').show();
        $(this).parent().parent().find('.text-comment').show();
    });

    $(document).on('click', '.cancel-comment-reply', function (e) {
        e.preventDefault();
        comment_id = $(this).attr('name');
        $(this).parent().parent().hide();
        $(this).parent().parent().prev().find('.edit_comment').show();
        $(this).parent().parent().prev().find('.del_comment').show();
        $(this).parent().parent().prev().find('.reply_comment').show();
    });
});

// Issue suggestion functionality
document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return;

    const suggestionBox = createSuggestionBox();
    const cache = new Map(); // Cache for API responses
    let debounceTimer = null;
    let currentSearch = '';
    let selectedIndex = -1;
    let isKeyboardNavigating = false;
    let isLoadingMore = false;
    let currentPage = 1;
    let hasMorePages = false;

    // Event listeners
    textarea.addEventListener('input', handleInput);
    textarea.addEventListener('keydown', handleKeyDown);
    textarea.addEventListener('click', handleTextareaClick);
    document.addEventListener('click', handleDocumentClick);

    // Main input handler with debounce
    function handleInput(e) {
        const { value, selectionStart } = e.target;
        const lastHashIndex = value.lastIndexOf('#', selectionStart);
        
        // Clear any existing timer
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }

        // Check if we're in a valid search context
        if (lastHashIndex === -1 || selectionStart <= lastHashIndex) {
            hideSuggestionBox();
            return;
        }

        const query = value.slice(lastHashIndex + 1, selectionStart);
        
        // Only search if we have a numeric query
        if (!/^\d+$/.test(query)) {
            hideSuggestionBox();
            return;
        }

        currentSearch = query;
        currentPage = 1; // Reset pagination when input changes
        
        // Implement a 250ms debounce for API calls
        debounceTimer = setTimeout(() => {
            fetchIssueSuggestions(query, currentPage);
        }, 250);
    }

    // Handle keyboard navigation
    function handleKeyDown(e) {
        if (!isBoxVisible()) return;

        const items = getSuggestionItems();
        if (!items.length) return;

        switch (e.key) {
            case 'ArrowDown':
            case 'ArrowUp':
                e.preventDefault();
                isKeyboardNavigating = true;
                
                selectedIndex = navigateSelection(
                    e.key === 'ArrowDown' ? 1 : -1,
                    selectedIndex,
                    items.length
                );
                
                updateSelectedItem(items, selectedIndex);
                
                // Ensure selected item is visible in the suggestion box
                if (selectedIndex >= 0) {
                    const selectedItem = items[selectedIndex];
                    ensureElementIsVisible(selectedItem, suggestionBox);
                }
                
                // Load more issues if we're at the bottom and there are more pages
                if (e.key === 'ArrowDown' && selectedIndex === items.length - 1 && hasMorePages && !isLoadingMore) {
                    loadMoreIssues();
                }
                break;

            case 'Enter':
                if (selectedIndex >= 0) {
                    e.preventDefault();
                    const selectedItem = items[selectedIndex];
                    const issueNumber = selectedItem.dataset.issueNumber;
                    insertIssueReference(issueNumber);
                    hideSuggestionBox();
                }
                break;

            case 'Escape':
                e.preventDefault();
                hideSuggestionBox();
                textarea.focus();
                break;
        }
    }

    // Handle clicks on the textarea
    function handleTextareaClick(e) {
        hideSuggestionBox();
    }

    // Handle clicks outside the suggestion box
    function handleDocumentClick(e) {
        // Close the box when clicking anywhere outside the box
        if (!suggestionBox.contains(e.target)) {
            hideSuggestionBox();
        }
    }

    // Create suggestion box once
    function createSuggestionBox() {
        const box = document.createElement('div');
        box.className = 'suggestion-box';
        box.style.cssText = `
            position: absolute;
            background: #fff;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            overflow-y: auto;
            scrollbar-width: none; /* Firefox */
            max-height: 150px;
            width: 300px;
            z-index: 1000;
            display: none;
        `;
        
        // Hide scrollbar for WebKit browsers
        const style = document.createElement('style');
        style.textContent = `
            .suggestion-box::-webkit-scrollbar {
                display: none;
            }
            .suggestion-item.selected {
                background-color: #f0f0f0;
            }
            .load-more {
                text-align: center;
                padding: 8px;
                color: #0366d6;
                cursor: pointer;
                font-weight: bold;
                background-color: #f6f8fa;
                border-top: 1px solid #e1e4e8;
            }
            .load-more:hover {
                background-color: #f0f0f0;
            }
            .loading {
                text-align: center;
                padding: 8px;
                color: #666;
                font-style: italic;
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(box);
        return box;
    }

    // Fetch issue suggestions with pagination
    async function fetchIssueSuggestions(query, page = 1, append = false) {
    if (query !== currentSearch) return;
    // Check cache first
    const cacheKey = `${query}-${page}`;
    if (cache.has(cacheKey)) {
        const cachedData = cache.get(cacheKey);
        displaySuggestions(cachedData.issues, append);
        hasMorePages = cachedData.hasMorePages;
        return;
    }
    
    try {
        if (!append) {
            displayLoadingIndicator();
        } else {
            appendLoadingIndicator();
        }
        
        // Get issues from backend API
        const url = `/api/v1/issues?page=${page}`;
        const response = await fetch(url);
        
        if (!response.ok) throw new Error('API request failed');
        
        const data = await response.json(); 

        // Check for pagination headers (if provided)
        const linkHeader = response.headers.get('Link');
        hasMorePages = linkHeader && linkHeader.includes('rel="next"');

        // Filter issues by number containing the query
        const filteredIssues = data.results
            .filter(issue => issue.id.toString().includes(query))
            .slice(0, 5); // Limit to 5 results per page

        // Cache the results
        cache.set(cacheKey, {
            issues: filteredIssues,
            hasMorePages: hasMorePages
        });

        if (query === currentSearch) {
            displaySuggestions(filteredIssues, append);
        }
    } catch (error) {
        console.error('Error fetching issues:', error);
        if (!append) {
            hideSuggestionBox();
        } else {
            removeLoadingIndicator();
        }
    } finally {
        isLoadingMore = false;
    }
}

    // Display loading indicator
    function displayLoadingIndicator() {
        suggestionBox.innerHTML = '<div class="loading">Loading suggestions...</div>';
        suggestionBox.style.display = 'block';
        positionSuggestionBox();
    }

    // Append loading indicator to the bottom
    function appendLoadingIndicator() {
        // Remove any existing loading indicators or load more buttons
        removeLoadingIndicator();
        removeLoadMoreButton();
        
        const loadingItem = document.createElement('div');
        loadingItem.className = 'loading';
        loadingItem.textContent = 'Loading more...';
        suggestionBox.appendChild(loadingItem);
    }

    // Remove loading indicator
    function removeLoadingIndicator() {
        const loadingItem = suggestionBox.querySelector('.loading');
        if (loadingItem) {
            loadingItem.remove();
        }
    }

    // Remove load more button
    function removeLoadMoreButton() {
        const loadMoreButton = suggestionBox.querySelector('.load-more');
        if (loadMoreButton) {
            loadMoreButton.remove();
        }
    }

    // Load more issues
    function loadMoreIssues() {
        if (isLoadingMore || !hasMorePages) return;
        
        isLoadingMore = true;
        currentPage++;
        fetchIssueSuggestions(currentSearch, currentPage, true);
    }

    // Display suggestions with improved positioning
    function displaySuggestions(issues, append = false) {
        if (!append) {
            // Clear previous suggestions
            suggestionBox.innerHTML = '';
        } else {
            // Remove loading indicator and load more button
            removeLoadingIndicator();
            removeLoadMoreButton();
        }
        
        if (!issues.length && !append) {
            hideSuggestionBox();
            return;
        }

        if (!append) {
            // Reset selection state
            selectedIndex = -1;
            isKeyboardNavigating = false;
        }

        // Add suggestion items
        issues.forEach(issue => {
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.dataset.issueNumber = issue.id;
            div.innerHTML = `<strong>#${issue.id}</strong>: ${escapeHTML(issue.description)}`;
            div.style.cssText = `
                padding: 8px 10px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
            `;
            
            div.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent document click from firing
                insertIssueReference(issue.id);
                hideSuggestionBox();
            });
            
            div.addEventListener('mouseover', () => {
                if (!isKeyboardNavigating) {
                    const items = getSuggestionItems();
                    items.forEach(item => item.classList.remove('selected'));
                    div.classList.add('selected');
                    selectedIndex = Array.from(items).indexOf(div);
                }
            });
            
            div.addEventListener('mouseout', () => {
                if (!isKeyboardNavigating) {
                    div.classList.remove('selected');
                }
            });
            
            suggestionBox.appendChild(div);
        });

        // Add "Load more" button if there are more pages
        if (hasMorePages) {
            const loadMoreButton = document.createElement('div');
            loadMoreButton.className = 'load-more';
            loadMoreButton.textContent = 'Load more...';
            loadMoreButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent document click from firing
                loadMoreIssues();
            });
            suggestionBox.appendChild(loadMoreButton);
        }

        // Position the suggestion box
        positionSuggestionBox();
        
        // Show the suggestion box
        suggestionBox.style.display = 'block';
    }

    // Ensure element is visible within scrollable container
    function ensureElementIsVisible(element, container) {
        const containerRect = container.getBoundingClientRect();
        const elementRect = element.getBoundingClientRect();
        
        if (elementRect.bottom > containerRect.bottom) {
            container.scrollTop += (elementRect.bottom - containerRect.bottom);
        } else if (elementRect.top < containerRect.top) {
            container.scrollTop -= (containerRect.top - elementRect.top);
        }
    }

    // Position the suggestion box relative to the cursor
    function positionSuggestionBox() {
        const textareaRect = textarea.getBoundingClientRect();
        const { scrollLeft, scrollTop } = document.documentElement;
        
        // Get cursor position
        const cursorPosition = getCursorCoordinates(textarea);
        
        // Position below cursor
        suggestionBox.style.left = `${textareaRect.left + cursorPosition.left + scrollLeft}px`;
        suggestionBox.style.top = `${textareaRect.top + cursorPosition.top + scrollTop + 20}px`;
        
        // Ensure box is within viewport
        const boxRect = suggestionBox.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        if (boxRect.right > viewportWidth) {
            suggestionBox.style.left = `${viewportWidth - boxRect.width - 10 + scrollLeft}px`;
        }
        
        if (boxRect.bottom > viewportHeight) {
            suggestionBox.style.top = `${textareaRect.top + cursorPosition.top - boxRect.height - 10 + scrollTop}px`;
        }
    }

    // Get coordinates of the cursor within the textarea
    function getCursorCoordinates(textarea) {
        const cursorPosition = textarea.selectionStart;
        const textBefore = textarea.value.substring(0, cursorPosition);
        
        // Create a mirror element
        const mirror = document.createElement('div');
        mirror.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            visibility: hidden;
            height: auto;
            width: ${textarea.clientWidth}px;
            padding: ${getComputedStyle(textarea).padding};
            border: ${getComputedStyle(textarea).border};
            white-space: pre-wrap;
            word-wrap: break-word;
            font: ${getComputedStyle(textarea).font};
            line-height: ${getComputedStyle(textarea).lineHeight};
        `;
        
        // Replace line breaks with <br> for proper rendering
        mirror.innerHTML = escapeHTML(textBefore).replace(/\n/g, '<br>');
        
        // Append a span to mark the cursor position
        const cursorMark = document.createElement('span');
        cursorMark.textContent = '|';
        mirror.appendChild(cursorMark);
        
        // Add mirror to the document
        document.body.appendChild(mirror);
        
        // Get the position of the cursor marker
        const cursorMarkRect = cursorMark.getBoundingClientRect();
        const mirrorRect = mirror.getBoundingClientRect();
        
        // Calculate position relative to textarea
        const left = cursorMarkRect.left - mirrorRect.left;
        const top = cursorMarkRect.top - mirrorRect.top;
        
        // Clean up
        document.body.removeChild(mirror);
        
        return { left, top };
    }

    // Hide the suggestion box
    function hideSuggestionBox() {
        suggestionBox.style.display = 'none';
        selectedIndex = -1;
        isKeyboardNavigating = false;
    }

    // Check if the suggestion box is visible
    function isBoxVisible() {
        return suggestionBox && suggestionBox.style.display !== 'none';
    }

    // Get all suggestion items
    function getSuggestionItems() {
        return suggestionBox.querySelectorAll('.suggestion-item');
    }

    // Update the selected item
    function updateSelectedItem(items, index) {
        items.forEach((item, idx) => {
            item.classList.toggle('selected', idx === index);
        });
    }

    // Navigate through items with wrapping
    function navigateSelection(direction, currentIndex, totalItems) {
        if (currentIndex === -1) {
            return direction > 0 ? 0 : totalItems - 1;
        }
        
        const newIndex = currentIndex + direction;
        
        if (newIndex < 0) {
            return totalItems - 1;
        } else if (newIndex >= totalItems) {
            return 0;
        }
        
        return newIndex;
    }

    // Insert issue reference
    function insertIssueReference(number) {
        const { value, selectionStart } = textarea;
        const lastHashIndex = value.lastIndexOf('#', selectionStart);
        
        if (lastHashIndex === -1) return;
        
        const textBefore = value.substring(0, lastHashIndex);
        const textAfter = value.substring(selectionStart);
        const newText = `${textBefore}#${number}${textAfter}`;
        
        textarea.value = newText;
        
        const newCursorPos = lastHashIndex + number.toString().length + 1;
        textarea.setSelectionRange(newCursorPos, newCursorPos);
        textarea.focus();
    }

    // Escape HTML to prevent XSS
    function escapeHTML(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});