// Main cheatsheet initialization and polling logic

const CheatsheetApp = {
  /**
   * Current app being displayed
   */
  currentApp: null,

  /**
   * Polling timer ID
   */
  pollTimer: null,

  /**
   * Last refresh trigger value
   */
  lastRefreshTrigger: null,

  /**
   * Initialize the application
   */
  async initialize() {
    console.log('Initializing Shortcut Cheatsheet...');

    try {
      // Load font size and apply
      await Keyboard.loadFontSize();

      // Initialize keyboard handlers
      Keyboard.initialize();

      // Initialize positioning
      await Positioning.initialize();

      // Start polling for focused window
      this.startPolling();

      // Check for refresh triggers from settings window
      this.checkRefreshTrigger();

      console.log('Cheatsheet initialized successfully');
    } catch (error) {
      console.error('Failed to initialize cheatsheet:', error);
      Display.showError('Failed to initialize application');
    }
  },

  /**
   * Start polling for focused window changes
   */
  startPolling() {
    // Initial poll
    this.pollFocusedWindow();

    // Set up interval
    this.pollTimer = setInterval(() => {
      this.pollFocusedWindow();
    }, CONSTANTS.POLL_INTERVAL);
  },

  /**
   * Stop polling
   */
  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  },

  /**
   * Poll for focused window and update shortcuts
   */
  async pollFocusedWindow() {
    try {
      // Get focused window
      const focusedWindow = await WindowDetection.getFocusedWindow();

      if (!focusedWindow) {
        return;
      }

      // Get app name
      const appName = WindowDetection.getAppName(focusedWindow);

      if (!appName) {
        return;
      }

      // Skip if it's our own window or settings window
      if (appName.includes('shortcut-cheatsheet') || appName.includes('settings')) {
        return;
      }

      // Check if app changed
      if (appName === this.currentApp) {
        // App hasn't changed, but check if we need to reposition
        // (in case window went fullscreen/windowed)
        await Positioning.updatePosition();
        return;
      }

      // App changed - load new shortcuts
      this.currentApp = appName;
      await this.loadShortcuts(appName);

      // Update position after loading
      await Positioning.updatePosition();
    } catch (error) {
      console.error('Error during polling:', error);
      // Don't show error to user on every poll failure
    }
  },

  /**
   * Load shortcuts for a specific app
   * @param {string} appName - The application name
   */
  async loadShortcuts(appName) {
    try {
      // Try to load app-specific shortcuts
      let shortcuts = await Storage.getAppShortcuts(appName);

      // Fall back to default if not found
      if (!shortcuts) {
        console.log(`No shortcuts found for ${appName}, using default`);
        shortcuts = await Storage.getAppShortcuts('default');
      }

      // Display shortcuts
      if (shortcuts) {
        await Display.renderShortcuts(shortcuts);
      } else {
        await Display.renderShortcuts({
          app_name: appName,
          shortcuts: [],
        });
      }
    } catch (error) {
      console.error(`Failed to load shortcuts for ${appName}:`, error);
      Display.showError('Failed to load shortcuts');
    }
  },

  /**
   * Check for refresh triggers from settings window
   */
  async checkRefreshTrigger() {
    try {
      const trigger = await Neutralino.storage.getData('refresh-trigger');

      if (trigger && trigger !== this.lastRefreshTrigger) {
        console.log('Refresh trigger detected, reloading shortcuts');
        this.lastRefreshTrigger = trigger;

        // Force reload current app
        if (this.currentApp) {
          await this.loadShortcuts(this.currentApp);
          await Positioning.updatePosition();
        }
      }
    } catch (error) {
      // Ignore errors - storage might not be initialized yet
    }

    // Check again in 500ms
    setTimeout(() => this.checkRefreshTrigger(), 500);
  },

  /**
   * Handle application shutdown
   */
  async shutdown() {
    console.log('Shutting down...');
    this.stopPolling();
    await Neutralino.app.exit();
  },
};

// Initialize when Neutralino is ready
Neutralino.init();

Neutralino.events.on('ready', () => {
  CheatsheetApp.initialize();
});

Neutralino.events.on('windowClose', () => {
  CheatsheetApp.shutdown();
});

// Export for global access
window.CheatsheetApp = CheatsheetApp;
