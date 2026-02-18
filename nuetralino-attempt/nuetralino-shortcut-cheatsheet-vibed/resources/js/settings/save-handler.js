// Save handler - save shortcuts and trigger refresh

const SaveHandler = {
  /**
   * Initialize save handler
   */
  initialize() {
    const saveButton = document.getElementById('save-button');
    const cancelButton = document.getElementById('cancel-button');

    saveButton.addEventListener('click', () => this.save());
    cancelButton.addEventListener('click', () => this.cancel());
  },

  /**
   * Save current shortcuts
   */
  async save() {
    if (!AppManager.currentApp) {
      alert('No application selected');
      return;
    }

    try {
      // Get shortcuts from table
      const shortcuts = ShortcutTable.getShortcuts();

      // Create data object
      const data = {
        app_name: AppManager.currentApp,
        shortcuts: shortcuts,
      };

      // Save to file
      const success = await Storage.saveAppShortcuts(AppManager.currentApp, data);

      if (!success) {
        alert('Failed to save shortcuts');
        return;
      }

      // Trigger refresh in cheatsheet window
      const timestamp = Date.now().toString();
      await Neutralino.storage.setData('refresh-trigger', timestamp);

      // Mark settings window as closed
      await Neutralino.storage.setData('settings-window-open', 'false');

      // Close window
      await Neutralino.app.exit();
    } catch (error) {
      console.error('Failed to save shortcuts:', error);
      alert('Failed to save shortcuts: ' + error.message);
    }
  },

  /**
   * Cancel without saving
   */
  async cancel() {
    try {
      // Mark settings window as closed
      await Neutralino.storage.setData('settings-window-open', 'false');

      // Close window
      await Neutralino.app.exit();
    } catch (error) {
      console.error('Failed to cancel:', error);
    }
  },
};

window.SaveHandler = SaveHandler;
