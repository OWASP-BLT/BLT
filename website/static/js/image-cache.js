/**
 * image-cache.js - Client-side image caching
 * 
 * This utility pre-fetches and caches images for offline use.
 * It uses both browser cache and IndexedDB.
 */

(function() {
    // Configuration
    const IMAGE_CACHE_NAME = 'blt-image-cache-v1';
    const MAX_IMAGES = 200; // Maximum number of images to store
    const CACHE_EXPIRY = 7 * 24 * 60 * 60 * 1000; // 7 days
    
    // Track which images are being processed to avoid duplicates
    const processingImages = new Set();
    
    /**
     * Register a new image for caching
     * @param {string} src - Image source URL
     * @returns {Promise} Promise that resolves when image is cached
     */
    function cacheImage(src) {
        if (!src || typeof src !== 'string') return Promise.resolve();
        
        // Skip if already processing
        if (processingImages.has(src)) return Promise.resolve();
        
        // Skip non-image URLs
        if (!isImageUrl(src)) return Promise.resolve();
        
        // Skip external domains if they don't have CORS headers
        const isSameDomain = isSameOrigin(src);
        if (!isSameDomain) {
            // We can try to fetch but it might fail due to CORS
            // For external images, we'll use a more lenient approach
            return fetchWithCache(src);
        }
        
        // Add to processing set
        processingImages.add(src);
        
        // Cache the image
        return fetchWithCache(src)
            .then(() => {
                // Clean up tracking set
                processingImages.delete(src);
            })
            .catch(err => {
                console.warn(`Failed to cache image ${src}:`, err);
                processingImages.delete(src);
            });
    }
    
    /**
     * Fetch an image and store it in the cache
     * @param {string} src - Image URL
     * @returns {Promise} Promise that resolves when the image is cached
     */
    function fetchWithCache(src) {
        // First try to fetch the image
        return fetch(src, { mode: 'no-cors' })
            .then(response => {
                // For no-cors responses, we can't access response properties
                // But we still want to cache the binary data
                if (response.type === 'opaque') {
                    return caches.open(IMAGE_CACHE_NAME)
                        .then(cache => cache.put(new Request(src), response.clone()));
                }
                
                // For normal responses, verify it's OK before caching
                if (!response.ok) {
                    throw new Error(`Failed to fetch image: ${response.statusText}`);
                }
                
                // Store in cache
                return caches.open(IMAGE_CACHE_NAME)
                    .then(cache => cache.put(new Request(src), response.clone()));
            });
    }
    
    /**
     * Check if a URL is an image URL
     * @param {string} url - URL to check
     * @returns {boolean} True if URL is an image
     */
    function isImageUrl(url) {
        const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'];
        const urlLower = url.toLowerCase();
        
        // Check if URL ends with an image extension
        return imageExtensions.some(ext => urlLower.endsWith(ext)) ||
               // Or if it contains image in the path
               urlLower.includes('/images/') ||
               urlLower.includes('/img/') ||
               // Or if it's from an image service
               urlLower.includes('media/') ||
               urlLower.includes('uploads/');
    }
    
    /**
     * Check if a URL is from the same origin as the current page
     * @param {string} url - URL to check
     * @returns {boolean} True if URL is from the same origin
     */
    function isSameOrigin(url) {
        try {
            const currentOrigin = window.location.origin;
            const urlOrigin = new URL(url, currentOrigin).origin;
            return currentOrigin === urlOrigin;
        } catch (e) {
            return false;
        }
    }
    
    /**
     * Scan the page for images and cache them
     */
    function cacheVisibleImages() {
        // Find all image elements
        const imgElements = document.querySelectorAll('img');
        
        // Find all elements with background images
        const elementsWithBackgroundImage = Array.from(document.querySelectorAll('*'))
            .filter(el => {
                const style = window.getComputedStyle(el);
                const backgroundImage = style.backgroundImage;
                return backgroundImage && backgroundImage !== 'none' && backgroundImage.includes('url(');
            });
            
        // Extract image URLs from img elements
        const imgUrls = Array.from(imgElements)
            .map(img => img.src)
            .filter(src => src); // Filter out empty URLs
            
        // Extract image URLs from background images
        const backgroundImgUrls = elementsWithBackgroundImage
            .map(el => {
                const style = window.getComputedStyle(el);
                const backgroundImage = style.backgroundImage;
                // Extract URL from the url('...') pattern
                const urlMatch = /url\(['"]?([^'"()]+)['"]?\)/g.exec(backgroundImage);
                return urlMatch ? urlMatch[1] : null;
            })
            .filter(src => src); // Filter out null values
            
        // Combine all URLs and remove duplicates
        const allImageUrls = [...new Set([...imgUrls, ...backgroundImgUrls])];
        
        // Cache each image
        allImageUrls.forEach(url => {
            cacheImage(url);
        });
    }
    
    /**
     * Clean old images from the cache
     * @returns {Promise} Promise that resolves when cleaning is complete
     */
    function cleanOldImages() {
        return caches.open(IMAGE_CACHE_NAME)
            .then(cache => {
                return cache.keys()
                    .then(requests => {
                        // If we have more than MAX_IMAGES, remove the oldest ones
                        if (requests.length > MAX_IMAGES) {
                            // Respect cache expiration
                            const now = Date.now();
                            const deletePromises = requests
                                .map(request => cache.match(request)
                                    .then(response => {
                                        if (!response) return null;
                                        
                                        // Check the date header to determine age
                                        const dateHeader = response.headers.get('date');
                                        if (dateHeader) {
                                            const timestamp = new Date(dateHeader).getTime();
                                            // If older than expiry, delete it
                                            if (now - timestamp > CACHE_EXPIRY) {
                                                return cache.delete(request);
                                            }
                                        }
                                        
                                        return null;
                                    })
                                )
                                .filter(p => p !== null); // Remove null promises
                                
                            return Promise.all(deletePromises);
                        }
                    });
            })
            .catch(err => {
                console.warn('Error cleaning image cache:', err);
            });
    }
    
    /**
     * Initialize image caching
     */
    function init() {
        // If Service Worker API is not available, exit
        if (!('serviceWorker' in navigator) && !('caches' in window)) {
            console.warn('Service Worker or Cache API not supported. Image caching disabled.');
            return;
        }
        
        // Watch for DOM changes to catch new images
        const observer = new MutationObserver(mutations => {
            // Some mutations may have added images, scan for them
            cacheVisibleImages();
        });
        
        // Start observing
        observer.observe(document.body, { 
            childList: true, 
            subtree: true,
            attributes: true,
            attributeFilter: ['src', 'style']
        });
        
        // Initial scan for images
        cacheVisibleImages();
        
        // Clean old images
        cleanOldImages();
        
        // Override Image constructor to intercept image loading
        const originalImage = window.Image;
        window.Image = function(width, height) {
            const img = new originalImage(width, height);
            
            // Watch for src attribute changes
            const originalSrcSetter = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src').set;
            
            Object.defineProperty(img, 'src', {
                set: function(value) {
                    // Call the original setter
                    originalSrcSetter.call(this, value);
                    
                    // Cache the image
                    if (value) {
                        cacheImage(value);
                    }
                }
            });
            
            return img;
        };
        
        console.log('Image caching initialized');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Expose API
    window.ImageCache = {
        cacheImage: cacheImage,
        cacheAllImages: cacheVisibleImages,
        clearCache: function() {
            return caches.delete(IMAGE_CACHE_NAME);
        }
    };
})(); 