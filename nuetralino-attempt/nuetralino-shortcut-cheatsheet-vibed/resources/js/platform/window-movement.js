// Window movement module - handles window positioning

const WindowMovement = {
  /**
   * Get work area (screen dimensions minus panels)
   * @returns {Promise<Object>} Work area with x, y, width, height
   */
  async getWorkArea() {
    try {
      const result = await Neutralino.os.execCommand('xprop -root _NET_WORKAREA');
      const match = result.stdOut.match(/=\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)/);

      if (match) {
        return {
          x: parseInt(match[1]),
          y: parseInt(match[2]),
          width: parseInt(match[3]),
          height: parseInt(match[4]),
        };
      }
    } catch (error) {
      console.error('Failed to get work area:', error);
    }

    // Fallback to window.screen dimensions
    return {
      x: 0,
      y: 0,
      width: window.screen.width,
      height: window.screen.height,
    };
  },

  /**
   * Get current window size
   * @returns {Promise<Object>} Window size with width and height
   */
  async getWindowSize() {
    try {
      const size = await Neutralino.window.getSize();
      return size;
    } catch (error) {
      console.error('Failed to get window size:', error);
      return { width: 400, height: 300 };
    }
  },

  /**
   * Calculate corner position for window
   * @param {string} vertical - 'top' or 'bottom'
   * @param {string} horizontal - 'left' or 'right'
   * @param {boolean} isFullscreen - Whether focused window is fullscreen
   * @returns {Promise<Object>} Position with x and y coordinates
   */
  async calculateCornerPosition(vertical, horizontal, isFullscreen = false) {
    const workArea = await this.getWorkArea();
    const windowSize = await this.getWindowSize();

    let x, y;

    // Horizontal position
    if (horizontal === 'left') {
      x = workArea.x + CONSTANTS.WINDOW_PADDING;
    } else {
      x = workArea.x + workArea.width - windowSize.width - CONSTANTS.WINDOW_PADDING;
    }

    // Vertical position
    if (vertical === 'top') {
      // When fullscreen, use y=0 to utilize hidden top bar space
      y = isFullscreen ? 0 : workArea.y + CONSTANTS.WINDOW_PADDING;
    } else {
      y = workArea.y + workArea.height - windowSize.height - CONSTANTS.WINDOW_PADDING;
    }

    return { x, y };
  },

  /**
   * Move window to specified corner
   * @param {string} vertical - 'top' or 'bottom'
   * @param {string} horizontal - 'left' or 'right'
   * @param {boolean} isFullscreen - Whether focused window is fullscreen
   */
  async moveToCorner(vertical, horizontal, isFullscreen = false) {
    try {
      const position = await this.calculateCornerPosition(vertical, horizontal, isFullscreen);
      await Neutralino.window.move(position.x, position.y);
    } catch (error) {
      console.error('Failed to move window:', error);
    }
  },
};

window.WindowMovement = WindowMovement;
