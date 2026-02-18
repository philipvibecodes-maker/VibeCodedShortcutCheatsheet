// Window detection module - interacts with window-calls extension via DBus

const WindowDetection = {
  /**
   * Cache for window list (to reduce DBus calls)
   */
  windowListCache: null,
  windowListCacheTime: 0,
  CACHE_TTL: 450, // Cache for 450ms (just under 500ms poll interval)

  /**
   * Get list of all open windows from window-calls extension
   * @returns {Promise<Array>} List of window objects
   */
  async getOpenWindows() {
    // Check cache
    const now = Date.now();
    if (this.windowListCache && (now - this.windowListCacheTime) < this.CACHE_TTL) {
      return this.windowListCache;
    }

    try {
      const cmd = `gdbus call --session \\
        --dest org.gnome.Shell \\
        --object-path /org/gnome/Shell/Extensions/Windows \\
        --method org.gnome.Shell.Extensions.Windows.List`;

      const result = await Neutralino.os.execCommand(cmd);

      // Parse output: ('{"windows": [...]}'',) format
      const output = result.stdOut.trim();
      const jsonMatch = output.match(/\('(.+)'[,)]/);

      if (jsonMatch) {
        const data = JSON.parse(jsonMatch[1]);
        this.windowListCache = data.windows || [];
        this.windowListCacheTime = now;
        return this.windowListCache;
      }

      return [];
    } catch (error) {
      console.error('Failed to get window list:', error);
      throw new Error('window-calls extension may not be installed');
    }
  },

  /**
   * Get details for a specific window
   * @param {number} windowId - Window ID
   * @returns {Promise<Object|null>} Window details or null
   */
  async getWindowDetails(windowId) {
    try {
      const cmd = `gdbus call --session \\
        --dest org.gnome.Shell \\
        --object-path /org/gnome/Shell/Extensions/Windows \\
        --method org.gnome.Shell.Extensions.Windows.Details ${windowId}`;

      const result = await Neutralino.os.execCommand(cmd);

      // Parse output
      const output = result.stdOut.trim();
      const jsonMatch = output.match(/\('(.+)'[,)]/);

      if (jsonMatch) {
        return JSON.parse(jsonMatch[1]);
      }

      return null;
    } catch (error) {
      console.error(`Failed to get window details for ${windowId}:`, error);
      return null;
    }
  },

  /**
   * Get currently focused window
   * @returns {Promise<Object|null>} Focused window object or null
   */
  async getFocusedWindow() {
    const windows = await this.getOpenWindows();
    const focusedWindow = windows.find(w => w.focus);

    if (!focusedWindow) {
      return null;
    }

    // Get full details including dimensions
    const details = await this.getWindowDetails(focusedWindow.id);
    return details;
  },

  /**
   * Check if a window is fullscreen
   * @param {Object} window - Window object with width, height, monitor properties
   * @returns {Promise<boolean>} True if window is fullscreen
   */
  async isWindowFullscreen(window) {
    if (!window || !window.width || !window.height) {
      return false;
    }

    try {
      // Get screen dimensions
      const workArea = await WindowMovement.getWorkArea();

      // Allow ±50px tolerance for panels and decorations
      const TOLERANCE = 50;

      const widthMatch = Math.abs(window.width - workArea.width) <= TOLERANCE;
      const heightMatch = Math.abs(window.height - workArea.height) <= TOLERANCE;

      return widthMatch && heightMatch;
    } catch (error) {
      console.error('Failed to check fullscreen status:', error);
      return false;
    }
  },

  /**
   * Get the application name from wm_class
   * @param {Object} window - Window object
   * @returns {string|null} Normalized application name
   */
  getAppName(window) {
    if (!window || !window.wm_class) {
      return null;
    }

    return Utils.normalizeAppName(window.wm_class);
  },
};

window.WindowDetection = WindowDetection;
