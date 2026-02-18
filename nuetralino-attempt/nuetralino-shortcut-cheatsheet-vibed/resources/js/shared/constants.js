// Shared constants

const CONSTANTS = {
  // Font size limits
  MIN_FONT_SIZE: 8,
  MAX_FONT_SIZE: 24,
  DEFAULT_FONT_SIZE: 12,

  // Polling interval (ms)
  POLL_INTERVAL: 500,

  // Window padding from screen edges (px)
  WINDOW_PADDING: 10,

  // Data directory
  DATA_DIR: '/resources/data/',

  // Config file
  CONFIG_FILE: '/resources/data/config.json',

  // Default corner positions
  DEFAULT_CORNER_V: 'top',
  DEFAULT_CORNER_H: 'right',
};

// Export for use in other modules
window.CONSTANTS = CONSTANTS;
