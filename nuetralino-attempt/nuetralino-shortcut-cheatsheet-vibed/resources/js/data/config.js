// Configuration management module

const Config = {
  /**
   * Load configuration from config.json
   * @returns {Promise<Object>} Configuration object
   */
  async getConfig() {
    try {
      const content = await Neutralino.filesystem.readFile(CONSTANTS.CONFIG_FILE);
      return JSON.parse(content);
    } catch (error) {
      console.log('Config file not found, using defaults');
      return this.getDefaultConfig();
    }
  },

  /**
   * Save configuration to config.json
   * @param {Object} config - Configuration object
   * @returns {Promise<boolean>} Success status
   */
  async saveConfig(config) {
    try {
      const content = JSON.stringify(config, null, 2);
      await Neutralino.filesystem.writeFile(CONSTANTS.CONFIG_FILE, content);
      return true;
    } catch (error) {
      console.error('Failed to save config:', error);
      return false;
    }
  },

  /**
   * Get default configuration
   * @returns {Object} Default configuration
   */
  getDefaultConfig() {
    return {
      font_size: CONSTANTS.DEFAULT_FONT_SIZE,
      corner_vertical: CONSTANTS.DEFAULT_CORNER_V,
      corner_horizontal: CONSTANTS.DEFAULT_CORNER_H,
    };
  },

  /**
   * Get current font size
   * @returns {Promise<number>} Font size in pixels
   */
  async getFontSize() {
    const config = await this.getConfig();
    return config.font_size || CONSTANTS.DEFAULT_FONT_SIZE;
  },

  /**
   * Save font size
   * @param {number} size - Font size in pixels
   * @returns {Promise<boolean>} Success status
   */
  async saveFontSize(size) {
    const config = await this.getConfig();
    config.font_size = size;
    return await this.saveConfig(config);
  },

  /**
   * Get current corner position
   * @returns {Promise<Object>} Object with vertical and horizontal positions
   */
  async getCornerPosition() {
    const config = await this.getConfig();
    return {
      vertical: config.corner_vertical || CONSTANTS.DEFAULT_CORNER_V,
      horizontal: config.corner_horizontal || CONSTANTS.DEFAULT_CORNER_H,
    };
  },

  /**
   * Save corner position
   * @param {string} vertical - 'top' or 'bottom'
   * @param {string} horizontal - 'left' or 'right'
   * @returns {Promise<boolean>} Success status
   */
  async saveCornerPosition(vertical, horizontal) {
    const config = await this.getConfig();
    config.corner_vertical = vertical;
    config.corner_horizontal = horizontal;
    return await this.saveConfig(config);
  },
};

window.Config = Config;
