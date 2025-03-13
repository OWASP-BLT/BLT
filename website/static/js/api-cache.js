/**
 * API Cache - Provides caching and offline support for API requests
 * This utility will cache API responses in localStorage for fallback
 * when network errors occur.
 */

const ApiCache = (() => {
  // Default cache expiration (12 hours in milliseconds)
  const DEFAULT_CACHE_EXPIRATION = 12 * 60 * 60 * 1000;
  
  // Max size for localStorage cache entries (3MB)
  const MAX_CACHE_SIZE = 3 * 1024 * 1024;
  
  // Create a namespace for our cache entries
  const CACHE_PREFIX = 'blt_api_cache_';
  
  /**
   * Fetch data from API with caching
   * @param {string} url - The API URL to fetch
   * @param {Object} options - Fetch options
   * @param {number} expiration - Cache expiration in milliseconds
   * @returns {Promise} - Promise resolving to the API response
   */
  const fetchWithCache = async (url, options = {}, expiration = DEFAULT_CACHE_EXPIRATION) => {
    const cacheKey = `${CACHE_PREFIX}${url}`;
    const cachedData = getFromCache(cacheKey);
    
    // Set default headers
    options.headers = options.headers || {};
    
    // If we only want cached data (offline mode)
    if (options.offlineOnly) {
      if (cachedData) {
        return Promise.resolve(cachedData.data);
      }
      return Promise.reject(new Error('No cached data available for offline use'));
    }
    
    // Try to fetch fresh data
    try {
      const response = await fetch(url, options);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Cache the successful response for future use
      setInCache(cacheKey, data, expiration);
      
      return data;
    } catch (error) {
      console.error('Network error:', error);
      
      // If we have cached data, return it
      if (cachedData) {
        // Add flag to indicate this is cached data
        return {
          ...cachedData.data,
          _fromCache: true,
          _cachedAt: cachedData.timestamp
        };
      }
      
      // No cached data, rethrow the error
      throw error;
    }
  };
  
  /**
   * Get data from cache
   * @param {string} key - Cache key
   * @returns {Object|null} - Cached data or null if not found/expired
   */
  const getFromCache = (key) => {
    try {
      const item = localStorage.getItem(key);
      
      if (!item) return null;
      
      const { data, timestamp, expiration } = JSON.parse(item);
      const now = Date.now();
      
      // Check if cache is expired
      if (now - timestamp > expiration) {
        localStorage.removeItem(key);
        return null;
      }
      
      return { data, timestamp };
    } catch (error) {
      console.error('Cache retrieval error:', error);
      return null;
    }
  };
  
  /**
   * Store data in cache
   * @param {string} key - Cache key
   * @param {Object} data - Data to cache
   * @param {number} expiration - Expiration time in milliseconds
   */
  const setInCache = (key, data, expiration) => {
    try {
      const cacheObject = {
        data,
        timestamp: Date.now(),
        expiration
      };
      
      const serialized = JSON.stringify(cacheObject);
      
      // Check if the serialized data is too large
      if (serialized.length > MAX_CACHE_SIZE) {
        console.warn('Cache entry too large, not caching:', key);
        return;
      }
      
      localStorage.setItem(key, serialized);
    } catch (error) {
      console.error('Cache storage error:', error);
      // If we hit the storage limit, clear some old entries
      if (error.name === 'QuotaExceededError') {
        clearOldEntries();
      }
    }
  };
  
  /**
   * Clear old cache entries to make space
   */
  const clearOldEntries = () => {
    try {
      const keys = [];
      
      // Get all cache keys
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.startsWith(CACHE_PREFIX)) {
          keys.push(key);
        }
      }
      
      // Sort by timestamp (oldest first) and remove 1/3 of entries
      const entriesToRemove = Math.max(1, Math.floor(keys.length / 3));
      
      const sortedKeys = keys.sort((a, b) => {
        const itemA = JSON.parse(localStorage.getItem(a));
        const itemB = JSON.parse(localStorage.getItem(b));
        return itemA.timestamp - itemB.timestamp;
      });
      
      // Remove oldest entries
      sortedKeys.slice(0, entriesToRemove).forEach(key => {
        localStorage.removeItem(key);
      });
      
      console.log(`Cleared ${entriesToRemove} old cache entries`);
    } catch (error) {
      console.error('Error clearing old entries:', error);
    }
  };
  
  /**
   * Clear all API cache entries
   */
  const clearAllCache = () => {
    try {
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const key = localStorage.key(i);
        if (key.startsWith(CACHE_PREFIX)) {
          localStorage.removeItem(key);
        }
      }
      console.log('API cache cleared');
    } catch (error) {
      console.error('Error clearing cache:', error);
    }
  };
  
  /**
   * Pre-cache specific API routes for offline use
   * @param {Array} urls - List of URLs to pre-cache
   */
  const precacheRoutes = async (urls = []) => {
    if (!urls.length) return;
    
    const promises = urls.map(url => {
      return fetch(url)
        .then(response => response.json())
        .then(data => {
          const cacheKey = `${CACHE_PREFIX}${url}`;
          setInCache(cacheKey, data, DEFAULT_CACHE_EXPIRATION);
          return { url, success: true };
        })
        .catch(error => {
          console.error(`Failed to precache ${url}:`, error);
          return { url, success: false, error };
        });
    });
    
    return Promise.all(promises);
  };
  
  // Return the public API
  return {
    fetch: fetchWithCache,
    clearCache: clearAllCache,
    precacheRoutes
  };
})();

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ApiCache;
} 