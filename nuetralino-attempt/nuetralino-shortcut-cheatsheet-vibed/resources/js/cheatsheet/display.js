// Display module - handles rendering shortcuts in the UI

const Display = {
  /**
   * Current app name being displayed
   */
  currentAppName: null,

  /**
   * Render shortcuts for an app
   * @param {Object} data - Shortcuts data object
   */
  async renderShortcuts(data) {
    const appLabel = document.getElementById('app-label');
    const shortcutsGrid = document.getElementById('shortcuts-grid');

    if (!data || !data.shortcuts || data.shortcuts.length === 0) {
      appLabel.textContent = 'No shortcuts';
      shortcutsGrid.innerHTML = '';
      await this.resizeToContent();
      return;
    }

    // Set app name
    this.currentAppName = data.app_name || 'Unknown';
    appLabel.textContent = Utils.formatAppName(this.currentAppName);

    // Clear existing shortcuts
    shortcutsGrid.innerHTML = '';

    // Render each shortcut
    data.shortcuts.forEach((shortcut, index) => {
      // Create shortcut row
      const row = document.createElement('div');
      row.className = 'shortcut-row';

      // Description
      const description = document.createElement('div');
      description.className = 'shortcut-description';
      description.textContent = shortcut.description;

      // Keys
      const keys = document.createElement('div');
      keys.className = 'shortcut-keys';
      keys.textContent = shortcut.keys;

      // Append to grid
      shortcutsGrid.appendChild(description);
      shortcutsGrid.appendChild(keys);

      // Add separator after each row except the last
      if (index < data.shortcuts.length - 1) {
        const separator = document.createElement('div');
        separator.className = 'shortcut-separator';
        shortcutsGrid.appendChild(separator);
      }
    });

    // Resize window to fit content
    await this.resizeToContent();
  },

  /**
   * Resize window to fit current content
   */
  async resizeToContent() {
    // Wait a tick for DOM to update
    await new Promise(resolve => setTimeout(resolve, 10));

    const container = document.getElementById('cheatsheet-container');
    const rect = container.getBoundingClientRect();

    // Calculate required size (add a bit of padding for safety)
    const width = Math.ceil(rect.width) + 2;
    const height = Math.ceil(rect.height) + 2;

    try {
      await Neutralino.window.setSize({
        width: width,
        height: height,
      });
    } catch (error) {
      console.error('Failed to resize window:', error);
    }
  },

  /**
   * Apply font size to CSS
   * @param {number} fontSize - Font size in pixels
   */
  applyFontSize(fontSize) {
    document.documentElement.style.setProperty('--font-size', `${fontSize}px`);
  },

  /**
   * Show error message
   * @param {string} message - Error message to display
   */
  showError(message) {
    const appLabel = document.getElementById('app-label');
    const shortcutsGrid = document.getElementById('shortcuts-grid');

    appLabel.textContent = 'Error';
    shortcutsGrid.innerHTML = `<div id="error-message">${message}</div>`;
  },
};

window.Display = Display;
