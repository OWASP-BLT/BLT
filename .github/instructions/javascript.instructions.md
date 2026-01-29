---
applyTo: "website/static/**/*.js"
---

# JavaScript Requirements for OWASP BLT

When creating or editing JavaScript files for OWASP BLT, follow these guidelines:

## Code Style and Standards

1. **Modern JavaScript** - Use ES6+ syntax
   ```javascript
   // Use const/let instead of var
   const API_URL = '/api/issues/';
   let currentPage = 1;
   
   // Arrow functions
   const fetchIssues = async () => {
       const response = await fetch(API_URL);
       return response.json();
   };
   ```

2. **No Console Statements** - Remove all console statements before committing
   - ❌ BAD: `console.log('debug info')`
   - ❌ BAD: `console.error('error')`
   - ✅ GOOD: Remove or comment out for production

3. **Strict Mode** - Use strict mode
   ```javascript
   'use strict';
   ```

## File Organization

1. **Separate Files** - Keep JavaScript in separate `.js` files
   - Place in `website/static/js/` directory
   - Load via Django template: `{% static 'js/myfile.js' %}`

2. **Module Pattern** - Use modules or IIFE to avoid global scope pollution
   ```javascript
   (function() {
       'use strict';
       
       // Your code here
   })();
   ```

## DOM Manipulation

1. **Use Modern DOM API** - Prefer vanilla JavaScript over jQuery
   ```javascript
   // Query selectors
   const element = document.querySelector('#myId');
   const elements = document.querySelectorAll('.myClass');
   
   // Event listeners
   element.addEventListener('click', handleClick);
   
   // Manipulation
   element.classList.add('active');
   element.textContent = 'New text';
   element.setAttribute('data-id', '123');
   ```

2. **Event Delegation** - For dynamic content
   ```javascript
   document.addEventListener('click', (e) => {
       if (e.target.matches('.delete-btn')) {
           handleDelete(e.target);
       }
   });
   ```

## Async Operations

1. **Use async/await** - For promises
   ```javascript
   async function fetchData() {
       try {
           const response = await fetch('/api/data/');
           const data = await response.json();
           return data;
       } catch (error) {
           handleError(error);
       }
   }
   ```

2. **Fetch API** - For AJAX requests
   ```javascript
   async function createIssue(data) {
       const response = await fetch('/api/issues/', {
           method: 'POST',
           headers: {
               'Content-Type': 'application/json',
               'X-CSRFToken': getCsrfToken()
           },
           body: JSON.stringify(data)
       });
       return response.json();
   }
   ```

## CSRF Token Handling

1. **Include CSRF Token** - For POST/PUT/DELETE requests
   ```javascript
   function getCsrfToken() {
       return document.querySelector('[name=csrfmiddlewaretoken]').value;
   }
   
   // Or from cookie
   function getCsrfTokenFromCookie() {
       const name = 'csrftoken';
       const cookies = document.cookie.split(';');
       for (let cookie of cookies) {
           const [key, value] = cookie.trim().split('=');
           if (key === name) return value;
       }
       return null;
   }
   ```

## Error Handling

1. **User-Friendly Messages** - Don't expose technical details
   ```javascript
   try {
       await saveData();
       showMessage('Data saved successfully', 'success');
   } catch (error) {
       // Log for debugging (remove console before commit)
       // console.error('Error:', error);
       showMessage('Unable to save data. Please try again.', 'error');
   }
   ```

2. **Graceful Degradation** - Handle errors gracefully
   ```javascript
   if (!response.ok) {
       throw new Error(`HTTP error! status: ${response.status}`);
   }
   ```

## Form Handling

1. **Form Validation** - Client-side validation
   ```javascript
   form.addEventListener('submit', async (e) => {
       e.preventDefault();
       
       if (!validateForm()) {
           return;
       }
       
       const formData = new FormData(form);
       await submitForm(formData);
   });
   ```

2. **FormData API** - For file uploads
   ```javascript
   const formData = new FormData();
   formData.append('title', title);
   formData.append('file', fileInput.files[0]);
   ```

## Performance

1. **Debouncing** - For frequent events
   ```javascript
   function debounce(func, wait) {
       let timeout;
       return function executedFunction(...args) {
           clearTimeout(timeout);
           timeout = setTimeout(() => func.apply(this, args), wait);
       };
   }
   
   const handleSearch = debounce(async (query) => {
       const results = await search(query);
       displayResults(results);
   }, 300);
   ```

2. **Lazy Loading** - Load content on demand
   ```javascript
   const observer = new IntersectionObserver((entries) => {
       entries.forEach(entry => {
           if (entry.isIntersecting) {
               loadMoreContent();
           }
       });
   });
   ```

## Code Comments

1. **Document Complex Logic**
   ```javascript
   /**
    * Fetches issues from the API with pagination and filtering
    * @param {number} page - Page number
    * @param {string} filter - Filter criteria
    * @returns {Promise<Object>} API response with issues
    */
   async function fetchIssues(page, filter) {
       // Implementation
   }
   ```

## Common Patterns

### Modal Management
```javascript
const modal = {
    element: document.querySelector('#modal'),
    
    open() {
        this.element.classList.remove('hidden');
    },
    
    close() {
        this.element.classList.add('hidden');
    },
    
    setContent(content) {
        this.element.querySelector('.modal-body').innerHTML = content;
    }
};
```

### API Client
```javascript
class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            ...options.headers
        };
        
        const response = await fetch(url, { ...options, headers });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        return response.json();
    }
    
    get(endpoint) {
        return this.request(endpoint);
    }
    
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
}

const api = new APIClient('/api');
```

### Notification System
```javascript
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
```

## Security Best Practices

1. **Sanitize User Input** - Prevent XSS
   ```javascript
   function sanitizeHTML(text) {
       const div = document.createElement('div');
       div.textContent = text;
       return div.innerHTML;
   }
   ```

2. **Validate Input** - Client-side validation
   ```javascript
   function validateEmail(email) {
       const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
       return re.test(email);
   }
   ```

3. **Use Content Security Policy** - Avoid inline scripts

## Testing

1. **Manual Testing** - Test in multiple browsers
2. **Console Errors** - Check browser console for errors
3. **Network Tab** - Verify API calls work correctly

## Best Practices Summary

✅ **DO**:
- Use modern ES6+ syntax
- Remove all console statements before committing
- Use const/let instead of var
- Use async/await for promises
- Include CSRF tokens in requests
- Handle errors gracefully
- Use event delegation for dynamic content
- Debounce frequent events
- Validate user input
- Write clear comments for complex logic
- Keep code modular and organized

❌ **DON'T**:
- Leave console statements in code
- Use var for variable declarations
- Pollute global scope
- Embed JavaScript in HTML templates
- Forget CSRF tokens
- Expose error details to users
- Skip error handling
- Use inline event handlers
- Trust user input without validation
- Create memory leaks with event listeners
