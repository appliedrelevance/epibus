import { useState, useEffect, useCallback } from 'react'
import ModbusDashboard from './components/ModbusDashboard'
import { fetchWrapper } from './utils/fetchWrapper'
import './App.css'

// Define the types for our Modbus data
export interface ModbusSignal {
  name: string;
  signal_name: string;
  signal_type: string;
  modbus_address: number;
  value: boolean | number | string;
}

export interface ModbusConnection {
  name: string;
  device_name: string;
  device_type: string;
  host: string;
  port: number;
  enabled: boolean;
  signals: ModbusSignal[];
}

// Define the type for real-time update messages
interface SignalUpdate {
  signal: string;
  value: boolean | number | string;
  timestamp?: string;
}

function App() {
  const [connections, setConnections] = useState<ModbusConnection[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdateSource, setLastUpdateSource] = useState<string>('');

  // Function to update a signal value in the connections state
  const updateSignalValue = useCallback((signalId: string, newValue: boolean | number | string, source: string) => {
    console.log(`Updating signal ${signalId} to ${newValue} (source: ${source})`);
    setLastUpdateSource(source);
    
    setConnections(prevConnections => {
      // Create a deep copy of the connections array to avoid mutating state
      return prevConnections.map(connection => {
        // Check if this connection contains the signal
        const signalIndex = connection.signals.findIndex(signal => signal.name === signalId);
        
        if (signalIndex !== -1) {
          // Create a new connection object with the updated signal
          const updatedConnection = { ...connection };
          updatedConnection.signals = [...connection.signals];
          updatedConnection.signals[signalIndex] = {
            ...updatedConnection.signals[signalIndex],
            value: newValue
          };
          return updatedConnection;
        }
        
        // Return the connection unchanged if it doesn't contain the signal
        return connection;
      });
    });
  }, []);

  // Set up local event listener for immediate UI updates
  useEffect(() => {
    const handleLocalUpdate = (event: Event) => {
      const customEvent = event as CustomEvent<SignalUpdate>;
      console.log('Received local update event:', customEvent.detail);
      
      if (customEvent.detail.signal && customEvent.detail.value !== undefined) {
        updateSignalValue(
          customEvent.detail.signal,
          customEvent.detail.value,
          'local'
        );
      }
    };

    // Add event listener for local updates
    window.addEventListener('local-signal-update', handleLocalUpdate);
    
    // Clean up event listener when component unmounts
    return () => {
      window.removeEventListener('local-signal-update', handleLocalUpdate);
    };
  }, [updateSignalValue]);

  // Set up real-time event listener
  useEffect(() => {
    // Function to handle real-time updates
    const handleRealtimeUpdate = (data: SignalUpdate) => {
      console.log('Received real-time update:', data);
      if (data.signal && data.value !== undefined) {
        updateSignalValue(data.signal, data.value, 'realtime');
      }
    };

    // Set up the event listener for Frappe's real-time events
    const setupSocketListener = () => {
      if (window.frappe && window.frappe.realtime) {
        console.log('Setting up real-time event listener');
        window.frappe.realtime.on('modbus_signal_update', handleRealtimeUpdate);
        return true;
      }
      return false;
    };

    // Try to set up the listener immediately
    let isSetup = setupSocketListener();
    
    // If not successful, try again after a delay (Frappe might not be fully loaded)
    if (!isSetup) {
      const intervalId = setInterval(() => {
        isSetup = setupSocketListener();
        if (isSetup) {
          clearInterval(intervalId);
          console.log('Real-time event listener set up successfully');
        }
      }, 1000);
      
      // Clean up interval if component unmounts
      return () => {
        clearInterval(intervalId);
        if (window.frappe && window.frappe.realtime) {
          window.frappe.realtime.off('modbus_signal_update', handleRealtimeUpdate);
        }
      };
    }
    
    // Clean up event listener when component unmounts
    return () => {
      if (window.frappe && window.frappe.realtime) {
        window.frappe.realtime.off('modbus_signal_update', handleRealtimeUpdate);
      }
    };
  }, [updateSignalValue]);

  // Initial data load
  useEffect(() => {
    fetchModbusData();
  }, []);

  const fetchModbusData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchWrapper('/api/method/epibus.www.warehouse_dashboard.get_modbus_data', {
        method: 'GET'
      });
      
      console.log('API Response:', data);
      setLastUpdateSource('api');
      
      // Handle different possible response structures from Frappe API
      if (data && data.message && Array.isArray(data.message)) {
        // Standard Frappe response with array in message property
        setConnections(data.message);
      } else if (data && Array.isArray(data)) {
        // Direct array response
        setConnections(data);
      } else if (data && typeof data === 'object' && data.message && typeof data.message === 'object') {
        // Response with nested object in message
        // Try to find an array property that might contain the connections
        const possibleArrays = Object.values(data.message).filter(val => Array.isArray(val));
        if (possibleArrays.length > 0) {
          // Use the first array found
          setConnections(possibleArrays[0] as ModbusConnection[]);
        } else {
          console.error('Could not find connections array in response:', data);
          throw new Error('Could not find connections array in response');
        }
      } else {
        console.error('Invalid data structure received:', data);
        throw new Error('Invalid data structure received');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching Modbus data:', err);
      // Log additional details for debugging
      console.error('Error details:', {
        errorType: err instanceof Error ? err.constructor.name : typeof err,
        errorStack: err instanceof Error ? err.stack : 'No stack trace available'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <ModbusDashboard
        connections={connections}
        loading={loading}
        error={error}
        onRefresh={fetchModbusData}
      />
      {/* Debug info - can be removed in production */}
      <div className="debug-info" style={{
        position: 'fixed',
        bottom: '5px',
        right: '5px',
        fontSize: '10px',
        color: '#999',
        backgroundColor: 'rgba(0,0,0,0.05)',
        padding: '2px 5px',
        borderRadius: '3px'
      }}>
        Last update: {lastUpdateSource || 'none'}
      </div>
    </div>
  );
}

// Add TypeScript interface for Frappe's global object
declare global {
  interface Window {
    frappe: {
      realtime: {
        on: (event: string, callback: (data: any) => void) => void;
        off: (event: string, callback: (data: any) => void) => void;
      };
    };
  }
}

export default App