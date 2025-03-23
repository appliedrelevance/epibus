import React, { useState, useEffect, useRef } from 'react';
import { ModbusSignal } from '../App';
import SignalRow from './SignalRow';
import { loadSortPreference, saveSortPreference } from '../utils/storageUtils';
import './SignalTable.css';

interface SignalTableProps {
  signals: ModbusSignal[];
  connectionId: string; // Added connectionId prop for unique storage keys
}

const SignalTable: React.FC<SignalTableProps> = ({ signals, connectionId }) => {
  // Use a ref to track if this is the first render
  const isInitialMount = useRef(true);
  // Initialize sort config from localStorage or default values
  const [sortConfig, setSortConfig] = useState<{
    key: keyof ModbusSignal | null;
    direction: 'asc' | 'desc';
  }>({
    key: null,
    direction: 'asc'
  });

  // Load saved sort preferences on component mount
  useEffect(() => {
    if (isInitialMount.current) {
      // Only load preferences on initial mount
      const savedPreference = loadSortPreference(connectionId);
      if (savedPreference.key) {
        setSortConfig({
          key: savedPreference.key as keyof ModbusSignal,
          direction: savedPreference.direction
        });
      }
      isInitialMount.current = false;
    }
  }, [connectionId]);

  // Log when signals change to help with debugging
  useEffect(() => {
    console.log(`SignalTable for ${connectionId} received updated signals (${signals.length} signals)`);
    // We don't reset sort config here, allowing it to persist across signal updates
  }, [signals, connectionId]);

  // Handle sorting
  const handleSort = (key: keyof ModbusSignal) => {
    let direction: 'asc' | 'desc' = 'asc';
    
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    
    // Update state
    setSortConfig({ key, direction });
    
    // Save to localStorage
    saveSortPreference(connectionId, key, direction);
  };
  
  // Sort signals based on current sort configuration
  const sortedSignals = React.useMemo(() => {
    const signalsCopy = [...signals];
    
    if (sortConfig.key) {
      signalsCopy.sort((a, b) => {
        const aValue = a[sortConfig.key!];
        const bValue = b[sortConfig.key!];
        
        if (aValue === bValue) return 0;
        
        // Handle different types of values
        if (typeof aValue === 'boolean' && typeof bValue === 'boolean') {
          return sortConfig.direction === 'asc' 
            ? (aValue ? 1 : -1) 
            : (aValue ? -1 : 1);
        }
        
        if (aValue === null || aValue === undefined) return 1;
        if (bValue === null || bValue === undefined) return -1;
        
        const comparison = String(aValue).localeCompare(String(bValue));
        return sortConfig.direction === 'asc' ? comparison : -comparison;
      });
    }
    
    return signalsCopy;
  }, [signals, sortConfig]);
  
  // Get sort indicator class
  const getSortIndicatorClass = (key: keyof ModbusSignal) => {
    if (sortConfig.key !== key) return 'fa-sort';
    return sortConfig.direction === 'asc' ? 'fa-sort-alpha-asc' : 'fa-sort-alpha-desc';
  };

  return (
    <table className="table table-sm table-hover">
      <thead>
        <tr>
          <th 
            className="sortable" 
            onClick={() => handleSort('signal_name')}
          >
            Signal Name 
            <span className="sort-indicator">
              <i className={`fa ${getSortIndicatorClass('signal_name')}`}></i>
            </span>
          </th>
          <th 
            className="sortable" 
            onClick={() => handleSort('signal_type')}
          >
            Type 
            <span className="sort-indicator">
              <i className={`fa ${getSortIndicatorClass('signal_type')}`}></i>
            </span>
          </th>
          <th 
            className="sortable" 
            onClick={() => handleSort('value')}
          >
            Value 
            <span className="sort-indicator">
              <i className={`fa ${getSortIndicatorClass('value')}`}></i>
            </span>
          </th>
          <th 
            className="sortable" 
            onClick={() => handleSort('modbus_address')}
          >
            Address 
            <span className="sort-indicator">
              <i className={`fa ${getSortIndicatorClass('modbus_address')}`}></i>
            </span>
          </th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {sortedSignals.map(signal => (
          <SignalRow 
            key={signal.name} 
            signal={signal} 
          />
        ))}
      </tbody>
    </table>
  );
};

export default SignalTable;