// Keyboard event handling module

const Keyboard = {
  /**
   * Current font size
   */
  currentFontSize: CONSTANTS.DEFAULT_FONT_SIZE,

  /**
   * Initialize keyboard event listeners
   */
  initialize() {
    document.addEventListener('keydown', (event) => this.handleKeyPress(event));

    // Close button
    const closeButton = document.getElementById('close-button');
    closeButton.addEventListener('click', () => this.handleClose());
  },

  /**
   * Handle keypress events
   * @param {KeyboardEvent} event - The keyboard event
   */
  async handleKeyPress(event) {
    const ctrl = event.ctrlKey;
    const key = event.key;

    // Font size controls
    if (ctrl && (key === '+' || key === '=')) {
      event.preventDefault();
      await this.increaseFontSize();
      return;
    }

    if (ctrl && key === '-') {
      event.preventDefault();
      await this.decreaseFontSize();
      return;
    }

    // Arrow keys for corner movement
    if (key.startsWith('Arrow')) {
      event.preventDefault();
      await Positioning.handleArrowKey(key);
      return;
    }

    // 'S' key to open settings
    if (key.toLowerCase() === 's' && !ctrl) {
      event.preventDefault();
      await this.openSettings();
      return;
    }

    // Escape to close
    if (key === 'Escape') {
      event.preventDefault();
      this.handleClose();
      return;
    }
  },

  /**
   * Increase font size
   */
  async increaseFontSize() {
    this.currentFontSize = Utils.clamp(
      this.currentFontSize + 1,
      CONSTANTS.MIN_FONT_SIZE,
      CONSTANTS.MAX_FONT_SIZE
    );
    await this.applyFontSize();
  },

  /**
   * Decrease font size
   */
  async decreaseFontSize() {
    this.currentFontSize = Utils.clamp(
      this.currentFontSize - 1,
      CONSTANTS.MIN_FONT_SIZE,
      CONSTANTS.MAX_FONT_SIZE
    );
    await this.applyFontSize();
  },

  /**
   * Apply current font size to UI
   */
  async applyFontSize() {
    // Update CSS
    Display.applyFontSize(this.currentFontSize);

    // Save to config
    await Config.saveFontSize(this.currentFontSize);

    // Resize window to fit new content size
    await Display.resizeToContent();

    // Reposition to corner
    await Positioning.updatePosition();
  },

  /**
   * Load saved font size
   */
  async loadFontSize() {
    this.currentFontSize = await Config.getFontSize();
    Display.applyFontSize(this.currentFontSize);
  },

  /**
   * Open settings window
   */
  async openSettings() {
    try {
      // Check if settings window is already open
      const isOpen = await Neutralino.storage.getData('settings-window-open');

      if (isOpen === 'true') {
        console.log('Settings window already open');
        return;
      }

      // Create settings window
      await Neutralino.window.create('/settings.html', {
        title: 'Shortcut Settings',
        width: 800,
        height: 600,
        center: true,
        resizable: true,
        alwaysOnTop: false,
        borderless: false,
      });

      // Mark settings as open
      await Neutralino.storage.setData('settings-window-open', 'true');
    } catch (error) {
      console.error('Failed to open settings:', error);
    }
  },

  /**
   * Handle close button/escape
   */
  handleClose() {
    Neutralino.app.exit();
  },
};

window.Keyboard = Keyboard;
