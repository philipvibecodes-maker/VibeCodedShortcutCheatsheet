// Shared utility functions

const Utils = {
  /**
   * Clamp a value between min and max
   */
  clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  },

  /**
   * Normalize app name (lowercase, remove special chars)
   */
  normalizeAppName(appName) {
    return appName.toLowerCase().replace(/[^a-z0-9-]/g, '');
  },

  /**
   * Format app name for display
   */
  formatAppName(appName) {
    // Capitalize first letter of each word
    return appName
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  },

  /**
   * Debounce function calls
   */
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
  },
};

window.Utils = Utils;
