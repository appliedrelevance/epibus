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
  const [connected, setConnected] = useState<boolean>(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<number>(0);

  // Function to update a signal value in the connections state
  const updateSignalValue = useCallback((signalId: string, newValue: boolean | number | string, source: string) => {
    console.log(`Updating signal ${signalId} to ${newValue} (source: ${source})`);
    setLastUpdateSource(source);
    setLastUpdateTime(Date.now());
    
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

  // Function to check PLC Bridge status by fetching signals
  const checkPLCStatus = useCallback(() => {
    console.log('🔄 Checking PLC Bridge status by fetching signals');
    fetchWrapper('/api/method/epibus.api.plc.get_signals', {
      method: 'GET'
    })
    .then(response => {
      console.log('✅ Signal fetch successful, PLC Bridge is connected:', response);
      setConnected(true);
      setLastUpdateTime(Date.now());
    })
    .catch(err => {
      console.error('❌ Error fetching signals, PLC Bridge may be disconnected:', err);
      setConnected(false);
    });
  }, []);
  
  // Set up real-time event listener using Frappe's socketio client
  useEffect(() => {
    // Function to handle real-time updates
    const handleRealtimeUpdate = (data: SignalUpdate) => {
      console.log('Received real-time update:', data);
      if (data.signal && data.value !== undefined) {
        updateSignalValue(data.signal, data.value, 'realtime');
        // We received a signal update, which means the PLC Bridge is working
        setConnected(true);
        setLastUpdateTime(Date.now());
      }
    };

    // Function to handle PLC Bridge status updates
    const handlePLCStatusUpdate = (data: any) => {
      console.log('📥 Received PLC Bridge status update:', data);
      if (data && typeof data.connected === 'boolean') {
        console.log(`🔄 Setting connected state to: ${data.connected}`);
        setConnected(data.connected);
        setLastUpdateTime(Date.now());
        console.log('✅ Updated connection status and timestamp');
      } else {
        console.warn('⚠️ Invalid PLC Bridge status data:', data);
      }
    };

    // Set up Frappe's real-time event listeners
    const setupFrappeListeners = () => {
      if (window.frappe && window.frappe.realtime) {
        console.log('🔄 Setting up Frappe realtime event listeners');
        
        // Listen for signal updates
        window.frappe.realtime.on('modbus_signal_update', handleRealtimeUpdate);
        
        // Listen for PLC Bridge status updates
        window.frappe.realtime.on('plc:status', handlePLCStatusUpdate);
        
        // Check connection status
        if (window.frappe.socketio && window.frappe.socketio.socket) {
          setConnected(window.frappe.socketio.socket.connected);
          
          // Set up connection listeners
          window.frappe.socketio.socket.on('connect', () => {
            console.log('🔌 Frappe socket connected');
            setConnected(true);
            checkPLCStatus();
          });
          
          window.frappe.socketio.socket.on('disconnect', () => {
            console.log('🔌 Frappe socket disconnected');
            setConnected(false);
          });
        }
        
        return true;
      }
      return false;
    };
    
    // Try to set up listeners immediately
    let isSetup = setupFrappeListeners();
    let intervalId: number | undefined;
    
    // If not ready, try again periodically
    if (!isSetup) {
      intervalId = window.setInterval(() => {
        isSetup = setupFrappeListeners();
        if (isSetup && intervalId) {
          window.clearInterval(intervalId);
        }
      }, 1000);
    }
    
    // Set up periodic status check
    const statusCheckInterval = window.setInterval(() => {
      if (window.frappe && window.frappe.socketio && 
          window.frappe.socketio.socket && window.frappe.socketio.socket.connected) {
        console.log('⏰ Periodic status check');
        checkPLCStatus();
      }
    }, 30000); // Every 30 seconds
    
    // Clean up
    return () => {
      if (intervalId) {
        window.clearInterval(intervalId);
      }
      
      window.clearInterval(statusCheckInterval);
      
      if (window.frappe && window.frappe.realtime) {
        window.frappe.realtime.off('modbus_signal_update', handleRealtimeUpdate);
        window.frappe.realtime.off('plc:status', handlePLCStatusUpdate);
      }
    };
  }, [updateSignalValue, checkPLCStatus]);

  // Initial data load and immediate status check
  useEffect(() => {
    console.log('🔄 Initial data load and status check');
    fetchModbusData();
    checkPLCStatus();
  }, [checkPLCStatus]);

  const fetchModbusData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchWrapper('/api/method/epibus.api.plc.get_signals', {
        method: 'GET'
      });
      
      console.log('API Response:', data);
      setLastUpdateSource('api');
      setLastUpdateTime(Date.now());
      
      try {
        // Check if this is the new response format from the PLC Bridge API (connections with nested signals)
        if (data && Array.isArray(data) && data.length > 0 && 'signals' in data[0]) {
          console.log('Detected new PLC Bridge API response format (connections with signals)');
          setConnections(data);
        }
        // Check if this is a response with connections in the message property
        else if (data && data.message && Array.isArray(data.message) &&
                data.message.length > 0 && 'signals' in data.message[0]) {
          console.log('Detected connections with signals in message property');
          setConnections(data.message);
        }
        // Direct array response
        else if (data && Array.isArray(data)) {
          console.log('Detected direct array response');
          setConnections(data);
        }
        // Response with nested object in message
        else if (data && typeof data === 'object' && data.message && typeof data.message === 'object') {
          // Try to find an array property that might contain the connections
          const possibleArrays = Object.values(data.message).filter(val => Array.isArray(val));
          if (possibleArrays.length > 0) {
            console.log('Found connections array in nested object');
            // Use the first array found
            setConnections(possibleArrays[0] as ModbusConnection[]);
          } else {
            console.error('Could not find connections array in response:', data);
            throw new Error('Could not find connections array in response');
          }
        }
        // Legacy format (flat list of signals) - this should no longer happen with the updated API
        else if (data && data.message && Array.isArray(data.message) &&
                data.message.length > 0 && 'name' in data.message[0] && 'value' in data.message[0]) {
          console.error('Received legacy flat signal list format - API should be updated');
          throw new Error('Received legacy format - falling back to warehouse dashboard API');
        }
        else {
          console.error('Invalid data structure received:', data);
          throw new Error('Invalid data structure received');
        }
      } catch (processingError) {
        console.error('Error processing API response:', processingError);
        
        // Fallback to the warehouse dashboard API
        console.log('Falling back to warehouse dashboard API...');
        const fallbackData = await fetchWrapper('/api/method/epibus.www.warehouse_dashboard.get_modbus_data', {
          method: 'GET'
        });
        
        console.log('Fallback API Response:', fallbackData);
        
        if (fallbackData && fallbackData.message && Array.isArray(fallbackData.message)) {
          setConnections(fallbackData.message);
          setLastUpdateSource('fallback-api');
        } else {
          throw new Error('Invalid data structure received from fallback API');
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching Modbus data:', err);
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
        connected={connected}
        lastUpdateTime={lastUpdateTime}
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

export default App
