// Application management - add/delete apps, populate selector

const AppManager = {
  /**
   * Current app name
   */
  currentApp: null,

  /**
   * All available apps
   */
  availableApps: [],

  /**
   * Initialize app manager
   */
  async initialize() {
    // Load available apps
    await this.loadAvailableApps();

    // Populate selector
    await this.populateSelector();

    // Set up event listeners
    const selector = document.getElementById('app-selector');
    const addButton = document.getElementById('add-app-button');
    const deleteButton = document.getElementById('delete-app-button');

    selector.addEventListener('change', () => this.switchApp());
    addButton.addEventListener('click', () => this.showAddAppMenu());
    deleteButton.addEventListener('click', () => this.deleteCurrentApp());

    // Load first app
    if (this.availableApps.length > 0) {
      this.currentApp = this.availableApps[0];
      await this.loadApp(this.currentApp);
    }
  },

  /**
   * Load available apps from storage
   */
  async loadAvailableApps() {
    this.availableApps = await Storage.getAllAppNames();
  },

  /**
   * Populate app selector dropdown
   */
  async populateSelector() {
    const selector = document.getElementById('app-selector');
    selector.innerHTML = '';

    if (this.availableApps.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'No apps configured';
      selector.appendChild(option);
      return;
    }

    this.availableApps.forEach(appName => {
      const option = document.createElement('option');
      option.value = appName;
      option.textContent = Utils.formatAppName(appName);
      selector.appendChild(option);
    });

    // Select current app
    if (this.currentApp) {
      selector.value = this.currentApp;
    }
  },

  /**
   * Switch to a different app
   */
  async switchApp() {
    const selector = document.getElementById('app-selector');
    const appName = selector.value;

    if (!appName) {
      return;
    }

    this.currentApp = appName;
    await this.loadApp(appName);
  },

  /**
   * Load shortcuts for a specific app
   * @param {string} appName - Application name
   */
  async loadApp(appName) {
    const data = await Storage.getAppShortcuts(appName);

    if (data && data.shortcuts) {
      ShortcutTable.loadShortcuts(data.shortcuts);
    } else {
      ShortcutTable.loadShortcuts([]);
    }
  },

  /**
   * Show add app menu with running apps
   */
  async showAddAppMenu() {
    const menu = document.getElementById('add-app-menu');
    const appsList = document.getElementById('running-apps-list');
    const cancelButton = document.getElementById('cancel-add-button');

    // Clear existing items
    appsList.innerHTML = '';

    try {
      // Get running apps
      const windows = await WindowDetection.getOpenWindows();
      const runningApps = new Set();

      windows.forEach(window => {
        const appName = WindowDetection.getAppName(window);
        if (appName && !this.availableApps.includes(appName)) {
          runningApps.add(appName);
        }
      });

      if (runningApps.size === 0) {
        appsList.innerHTML = '<p style="color: #999;">No new applications detected</p>';
      } else {
        runningApps.forEach(appName => {
          const item = document.createElement('div');
          item.className = 'app-item';
          item.textContent = Utils.formatAppName(appName);
          item.addEventListener('click', () => this.addApp(appName));
          appsList.appendChild(item);
        });
      }

      // Show menu
      menu.classList.remove('hidden');
    } catch (error) {
      console.error('Failed to get running apps:', error);
      appsList.innerHTML = '<p style="color: #ff8888;">Failed to detect running applications</p>';
      menu.classList.remove('hidden');
    }

    // Cancel button
    cancelButton.addEventListener('click', () => {
      menu.classList.add('hidden');
    });
  },

  /**
   * Add a new app
   * @param {string} appName - Application name
   */
  async addApp(appName) {
    // Create empty shortcuts file
    const data = {
      app_name: appName,
      shortcuts: [],
    };

    await Storage.saveAppShortcuts(appName, data);

    // Reload available apps
    await this.loadAvailableApps();
    await this.populateSelector();

    // Switch to new app
    this.currentApp = appName;
    const selector = document.getElementById('app-selector');
    selector.value = appName;
    await this.loadApp(appName);

    // Hide menu
    const menu = document.getElementById('add-app-menu');
    menu.classList.add('hidden');
  },

  /**
   * Delete current app
   */
  async deleteCurrentApp() {
    if (!this.currentApp) {
      return;
    }

    // Confirm deletion
    const confirmed = confirm(`Delete shortcuts for ${Utils.formatAppName(this.currentApp)}?`);

    if (!confirmed) {
      return;
    }

    // Delete app
    await Storage.deleteAppShortcuts(this.currentApp);

    // Reload available apps
    await this.loadAvailableApps();
    await this.populateSelector();

    // Load first available app
    if (this.availableApps.length > 0) {
      this.currentApp = this.availableApps[0];
      const selector = document.getElementById('app-selector');
      selector.value = this.currentApp;
      await this.loadApp(this.currentApp);
    } else {
      this.currentApp = null;
      ShortcutTable.clear();
    }
  },
};

window.AppManager = AppManager;
