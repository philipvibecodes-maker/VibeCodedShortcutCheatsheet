// Shortcut table management

const ShortcutTable = {
  /**
   * Initialize table
   */
  initialize() {
    const tbody = document.getElementById('shortcuts-tbody');
    const addButton = document.getElementById('add-shortcut-button');

    addButton.addEventListener('click', () => this.addRow('', ''));
  },

  /**
   * Add a new row to the table
   * @param {string} description - Shortcut description
   * @param {string} keys - Keyboard keys
   */
  addRow(description = '', keys = '') {
    const tbody = document.getElementById('shortcuts-tbody');
    const row = tbody.insertRow();

    // Description cell
    const descCell = row.insertCell();
    const descInput = document.createElement('input');
    descInput.type = 'text';
    descInput.value = description;
    descInput.placeholder = 'Enter description...';
    descCell.appendChild(descInput);

    // Keys cell
    const keysCell = row.insertCell();
    const keysInput = document.createElement('input');
    keysInput.type = 'text';
    keysInput.value = keys;
    keysInput.placeholder = 'Enter keys...';
    keysCell.appendChild(keysInput);

    // Actions cell
    const actionsCell = row.insertCell();
    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete-row-button';
    deleteButton.textContent = 'Delete';
    deleteButton.addEventListener('click', () => this.deleteRow(row));
    actionsCell.appendChild(deleteButton);

    // Focus on description input
    descInput.focus();
  },

  /**
   * Delete a row from the table
   * @param {HTMLTableRowElement} row - Row to delete
   */
  deleteRow(row) {
    row.remove();
  },

  /**
   * Clear all rows from the table
   */
  clear() {
    const tbody = document.getElementById('shortcuts-tbody');
    tbody.innerHTML = '';
  },

  /**
   * Load shortcuts into the table
   * @param {Array} shortcuts - Array of shortcut objects
   */
  loadShortcuts(shortcuts) {
    this.clear();

    if (!shortcuts || shortcuts.length === 0) {
      // Add one empty row
      this.addRow('', '');
      return;
    }

    shortcuts.forEach(shortcut => {
      this.addRow(shortcut.description, shortcut.keys);
    });
  },

  /**
   * Get current shortcuts from table
   * @returns {Array} Array of shortcut objects
   */
  getShortcuts() {
    const tbody = document.getElementById('shortcuts-tbody');
    const rows = tbody.querySelectorAll('tr');
    const shortcuts = [];

    rows.forEach(row => {
      const descInput = row.cells[0].querySelector('input');
      const keysInput = row.cells[1].querySelector('input');

      const description = descInput.value.trim();
      const keys = keysInput.value.trim();

      // Only include non-empty shortcuts
      if (description && keys) {
        shortcuts.push({ description, keys });
      }
    });

    return shortcuts;
  },
};

window.ShortcutTable = ShortcutTable;
