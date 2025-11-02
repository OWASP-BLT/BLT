/**
 * JavaScript functions for the invite organization page
 * Handles copy to clipboard functionality for referral links and email content
 */

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.warn('copyToClipboard: element not found', elementId);
        return;
    }
    const text = 'value' in element ? element.value : element.textContent || '';
    
    // Feature-detect clipboard API; fallback to manual selection
    const write = navigator.clipboard && typeof navigator.clipboard.writeText === 'function'
        ? navigator.clipboard.writeText(text)
        : Promise.reject(new Error('Clipboard API not available'));
    write.then(function() {
        // Show success feedback
        const button = document.querySelector(`button[onclick="copyToClipboard('${elementId}')"]`);
        if (button) {
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.classList.add('bg-green-500', 'text-white');
            button.classList.remove('bg-gray-200', 'hover:bg-gray-300', 'text-gray-700');
            
            setTimeout(function() {
                button.textContent = originalText;
                button.classList.remove('bg-green-500', 'text-white');
                button.classList.add('bg-gray-200', 'hover:bg-gray-300', 'text-gray-700');
            }, 2000);
        }
    }).catch(function(err) {
        console.error('Failed to copy text: ', err);
        alert('Unable to copy automatically. Please select and copy the text manually.');
        // Fallback: Select text for manual copy
        selectText(element);
    });
}

function copyEmailContent() {
    const subject = document.getElementById('email-subject').textContent;
    const body = document.getElementById('email-body').textContent;
    const fullContent = `Subject: ${subject}\n\n${body}`;
    
    (navigator.clipboard && typeof navigator.clipboard.writeText === 'function'
        ? navigator.clipboard.writeText(fullContent)
        : Promise.reject(new Error('Clipboard API not available'))
    ).then(function() {
        // Show success feedback
        const button = document.querySelector('button[onclick="copyEmailContent()"]');
        if (button) {
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.classList.add('bg-green-500');
            button.classList.remove('bg-[#e74c3c]', 'hover:bg-red-600');
            
            setTimeout(function() {
                button.textContent = originalText;
                button.classList.remove('bg-green-500');
                button.classList.add('bg-[#e74c3c]', 'hover:bg-red-600');
            }, 2000);
        }
    }).catch(function(err) {
        console.error('Failed to copy text: ', err);
        // Fallback: select the email body to aid manual copy
        const bodyEl = document.getElementById('email-body');
        if (bodyEl) selectText(bodyEl);
        alert('Copy requires HTTPS or user gesture. Text selected for manual copy.');
    });
}

function selectText(element) {
    if (!element) return;
    if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
        element.focus();
        element.select();
        return;
    }
    const range = document.createRange();
    range.selectNodeContents(element);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
}