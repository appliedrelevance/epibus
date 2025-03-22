import { useState, useEffect } from 'react'
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

function App() {
  const [connections, setConnections] = useState<ModbusConnection[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Initial data load
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
    </div>
  );
}

export default App