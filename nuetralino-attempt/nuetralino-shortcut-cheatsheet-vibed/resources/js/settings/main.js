// Settings window main initialization

const SettingsApp = {
  /**
   * Initialize the settings window
   */
  async initialize() {
    console.log('Initializing Settings...');

    try {
      // Initialize modules
      ShortcutTable.initialize();
      SaveHandler.initialize();

      // Load apps and initialize app manager
      await AppManager.initialize();

      console.log('Settings initialized successfully');
    } catch (error) {
      console.error('Failed to initialize settings:', error);
      alert('Failed to initialize settings: ' + error.message);
    }
  },

  /**
   * Handle window close
   */
  async shutdown() {
    console.log('Settings window closing...');

    try {
      // Mark settings window as closed
      await Neutralino.storage.setData('settings-window-open', 'false');
    } catch (error) {
      console.error('Failed to cleanup on shutdown:', error);
    }
  },
};

// Initialize when Neutralino is ready
Neutralino.init();

Neutralino.events.on('ready', () => {
  SettingsApp.initialize();
});

Neutralino.events.on('windowClose', () => {
  SettingsApp.shutdown();
});

// Export for global access
window.SettingsApp = SettingsApp;
