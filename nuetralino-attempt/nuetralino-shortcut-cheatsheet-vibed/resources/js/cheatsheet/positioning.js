// Positioning module - handles corner movement and positioning logic

const Positioning = {
  /**
   * Current corner position
   */
  cornerVertical: CONSTANTS.DEFAULT_CORNER_V,
  cornerHorizontal: CONSTANTS.DEFAULT_CORNER_H,

  /**
   * Initialize positioning from saved config
   */
  async initialize() {
    const position = await Config.getCornerPosition();
    this.cornerVertical = position.vertical;
    this.cornerHorizontal = position.horizontal;

    // Move to initial corner
    await this.updatePosition();
  },

  /**
   * Update window position based on current corner settings
   */
  async updatePosition() {
    // Check if focused window is fullscreen
    let isFullscreen = false;
    try {
      const focusedWindow = await WindowDetection.getFocusedWindow();
      if (focusedWindow) {
        isFullscreen = await WindowDetection.isWindowFullscreen(focusedWindow);
      }
    } catch (error) {
      // Ignore errors, use default fullscreen=false
    }

    // Move to corner
    await WindowMovement.moveToCorner(
      this.cornerVertical,
      this.cornerHorizontal,
      isFullscreen
    );
  },

  /**
   * Move to a specific corner
   * @param {string} vertical - 'top' or 'bottom'
   * @param {string} horizontal - 'left' or 'right'
   */
  async moveToCorner(vertical, horizontal) {
    this.cornerVertical = vertical;
    this.cornerHorizontal = horizontal;

    // Save to config
    await Config.saveCornerPosition(vertical, horizontal);

    // Update position
    await this.updatePosition();
  },

  /**
   * Handle arrow key press
   * @param {string} key - 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'
   */
  async handleArrowKey(key) {
    switch (key) {
      case 'ArrowUp':
        await this.moveToCorner('top', this.cornerHorizontal);
        break;
      case 'ArrowDown':
        await this.moveToCorner('bottom', this.cornerHorizontal);
        break;
      case 'ArrowLeft':
        await this.moveToCorner(this.cornerVertical, 'left');
        break;
      case 'ArrowRight':
        await this.moveToCorner(this.cornerVertical, 'right');
        break;
    }
  },
};

window.Positioning = Positioning;
