/**
 * Utility functions for working with localStorage to persist user preferences
 */

// Storage key prefix to avoid conflicts with other applications
const STORAGE_KEY_PREFIX = 'epibus_warehouse_dashboard_';

/**
 * Save sorting configuration to localStorage
 * 
 * @param connectionId - The ID of the connection (used to create unique keys for each table)
 * @param sortKey - The field name to sort by
 * @param sortDirection - The sort direction ('asc' or 'desc')
 */
export const saveSortPreference = (
  connectionId: string,
  sortKey: string | null,
  sortDirection: 'asc' | 'desc'
): void => {
  try {
    if (!sortKey) return;
    
    const storageKey = `${STORAGE_KEY_PREFIX}sort_${connectionId}`;
    const sortConfig = { key: sortKey, direction: sortDirection };
    localStorage.setItem(storageKey, JSON.stringify(sortConfig));
    
    console.log(`Saved sort preference for ${connectionId}: ${sortKey} ${sortDirection}`);
  } catch (error) {
    console.error('Error saving sort preference to localStorage:', error);
  }
};

/**
 * Load sorting configuration from localStorage
 * 
 * @param connectionId - The ID of the connection
 * @returns The saved sort configuration or default values if none exists
 */
export const loadSortPreference = (
  connectionId: string
): { key: string | null; direction: 'asc' | 'desc' } => {
  try {
    const storageKey = `${STORAGE_KEY_PREFIX}sort_${connectionId}`;
    const savedConfig = localStorage.getItem(storageKey);
    
    if (savedConfig) {
      const parsedConfig = JSON.parse(savedConfig);
      console.log(`Loaded sort preference for ${connectionId}: ${parsedConfig.key} ${parsedConfig.direction}`);
      return parsedConfig;
    }
  } catch (error) {
    console.error('Error loading sort preference from localStorage:', error);
  }
  
  // Default sort configuration if nothing is saved
  return { key: null, direction: 'asc' };
};

/**
 * Clear all sorting preferences from localStorage
 */
export const clearAllSortPreferences = (): void => {
  try {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith(STORAGE_KEY_PREFIX)) {
        localStorage.removeItem(key);
      }
    });
    console.log('Cleared all sort preferences');
  } catch (error) {
    console.error('Error clearing sort preferences from localStorage:', error);
  }
};