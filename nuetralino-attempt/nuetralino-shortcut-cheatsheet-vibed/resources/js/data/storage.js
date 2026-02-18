// Data storage module - handles reading/writing JSON files

const Storage = {
  /**
   * Get shortcuts for a specific app
   * @param {string} appName - The application name
   * @returns {Promise<Object|null>} The shortcuts data or null if not found
   */
  async getAppShortcuts(appName) {
    try {
      const filePath = `${CONSTANTS.DATA_DIR}${appName}.json`;
      const content = await Neutralino.filesystem.readFile(filePath);
      return JSON.parse(content);
    } catch (error) {
      console.error(`Failed to load shortcuts for ${appName}:`, error);
      return null;
    }
  },

  /**
   * Save shortcuts for a specific app
   * @param {string} appName - The application name
   * @param {Object} shortcuts - The shortcuts data
   * @returns {Promise<boolean>} Success status
   */
  async saveAppShortcuts(appName, shortcuts) {
    try {
      const filePath = `${CONSTANTS.DATA_DIR}${appName}.json`;
      const content = JSON.stringify(shortcuts, null, 2);
      await Neutralino.filesystem.writeFile(filePath, content);
      return true;
    } catch (error) {
      console.error(`Failed to save shortcuts for ${appName}:`, error);
      return false;
    }
  },

  /**
   * Get all available app names (from JSON files)
   * @returns {Promise<string[]>} List of app names
   */
  async getAllAppNames() {
    try {
      const entries = await Neutralino.filesystem.readDirectory(CONSTANTS.DATA_DIR);
      return entries
        .filter(entry => entry.type === 'FILE' && entry.entry.endsWith('.json'))
        .filter(entry => entry.entry !== 'config.json') // Exclude config file
        .map(entry => entry.entry.replace('.json', ''));
    } catch (error) {
      console.error('Failed to list app files:', error);
      return [];
    }
  },

  /**
   * Delete shortcuts for a specific app
   * @param {string} appName - The application name
   * @returns {Promise<boolean>} Success status
   */
  async deleteAppShortcuts(appName) {
    try {
      const filePath = `${CONSTANTS.DATA_DIR}${appName}.json`;
      await Neutralino.filesystem.removeFile(filePath);
      return true;
    } catch (error) {
      console.error(`Failed to delete shortcuts for ${appName}:`, error);
      return false;
    }
  },
};

window.Storage = Storage;
