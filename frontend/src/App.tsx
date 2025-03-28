import { useState, useEffect } from 'react'
import ModbusDashboard from './components/ModbusDashboard'
import { SignalMonitorProvider } from './contexts/SignalMonitorContext'
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
  const [lastUpdateSource, setLastUpdateSource] = useState<string>('');

  // Set up local event listener for immediate UI updates
  useEffect(() => {
    const handleLocalUpdate = (event: Event) => {
      const customEvent = event as CustomEvent<{
        signal: string;
        value: boolean | number | string;
        timestamp: number;
        source: string;
      }>;
      
      setLastUpdateSource(customEvent.detail.source || 'local');
    };

    // Add event listener for local updates
    window.addEventListener('local-signal-update', handleLocalUpdate);
    
    // Clean up event listener when component unmounts
    return () => {
      window.removeEventListener('local-signal-update', handleLocalUpdate);
    };
  }, []);

  // Initial data load
  useEffect(() => {
    fetchModbusData();
  }, []);

  const fetchModbusData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to fetch from the warehouse dashboard API
      try {
        const fallbackData = await fetch('/api/method/epibus.www.warehouse_dashboard.get_modbus_data')
          .then(response => {
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
          });
        
        if (fallbackData && fallbackData.message && Array.isArray(fallbackData.message)) {
          setConnections(fallbackData.message);
          setLastUpdateSource('api');
        } else {
          throw new Error('Invalid data structure received from API');
        }
      } catch (err) {
        console.error('Error fetching Modbus data:', err);
        setError('Failed to load connection data. Please try again later.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <SignalMonitorProvider>
      <div className="app-container">
        <ModbusDashboard
          connections={connections}
          loading={loading}
          error={error}
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
    </SignalMonitorProvider>
  );
}

export default App
