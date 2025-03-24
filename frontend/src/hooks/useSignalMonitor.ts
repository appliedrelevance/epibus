import { useState, useEffect, useCallback } from 'react';
import io, { Socket } from 'socket.io-client';

interface SignalValue {
  value: boolean | number;
  timestamp: number;
}

interface SignalUpdateEvent {
  signal: string;
  value: boolean | number;
  timestamp: number;
}

export function useSignalMonitor() {
  const [signals, setSignals] = useState<Record<string, SignalValue>>({});
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [socketInstance, setSocketInstance] = useState<Socket | null>(null);
  const [connected, setConnected] = useState(false);

  // Initialize socket connection
  useEffect(() => {
    console.log('🔌 Initializing Frappe socket connection...');
    
    // Connect to the Socket.IO server in the peer container
    // Using window.location.hostname ensures it works in the container network
    const socket = io(`${window.location.protocol}//${window.location.hostname}:9000`, {
      transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
      console.log('✅ Connected to Frappe socket with ID:', socket.id);
      setConnected(true);
      
      // Emit a join event to subscribe to Frappe real-time events
      socket.emit('join', {
        doctype: '*',
        docname: '*'
      });
      console.log('✅ Joined Frappe realtime channels');
    });

    socket.on('disconnect', () => {
      console.log('❌ Disconnected from Frappe socket');
      setConnected(false);
    });

    socket.on('modbus_signal_update', (data: SignalUpdateEvent) => {
      console.log(`🔄 Signal update received via socket.io: ${data.signal} = ${data.value}`);
      
      // Check if we already have this signal in our state
      setSignals(prev => {
        const prevValue = prev[data.signal]?.value;
        const hasChanged = prevValue !== data.value;
        
        if (hasChanged) {
          console.log(`📊 Updating signal value: ${data.signal} from ${prevValue} to ${data.value}`);
        } else {
          console.log(`📊 Signal value unchanged: ${data.signal} = ${data.value}`);
        }
        
        return {
          ...prev,
          [data.signal]: {
            value: data.value,
            timestamp: data.timestamp || Date.now()
          }
        };
      });
    });

    setSocketInstance(socket);

    return () => {
      console.log('👋 Closing socket connection');
      socket.close();
    };
  }, []);

  // Function to write a signal value
  const writeSignal = useCallback((signalName: string, value: boolean | number) => {
    console.log(`✏️ Writing signal: ${signalName} = ${value}`);
    
    // First try to write using the PLC Bridge API
    return fetch('/api/method/epibus.api.plc.update_signal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': localStorage.getItem('csrf_token') || ''
      },
      body: JSON.stringify({
        signal_id: signalName,
        value: value
      })
    })
    .then(response => response.json())
    .then(data => {
      console.log('Signal write response from PLC Bridge API:', data);
      return data.success;
    })
    .catch(error => {
      console.error('❌ Error writing signal via PLC Bridge API:', error);
      console.log('Falling back to warehouse dashboard API...');
      
      // Fallback to the warehouse dashboard API
      return fetch('/api/method/epibus.www.warehouse_dashboard.set_signal_value', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Frappe-CSRF-Token': localStorage.getItem('csrf_token') || ''
        },
        body: JSON.stringify({
          signal_id: signalName,
          value: value
        })
      })
      .then(response => response.json())
      .then(fallbackData => {
        console.log('Signal write response from fallback API:', fallbackData);
        return fallbackData.status === 'success';
      })
      .catch(fallbackError => {
        console.error('❌ Error writing signal via fallback API:', fallbackError);
        return false;
      });
    });
  }, []);

  // Load initial signals
  useEffect(() => {
    // Get signals from the PLC Bridge API
    fetch('/api/method/epibus.api.plc.get_signals')
      .then(response => response.json())
      .then(data => {
        const initialSignals: Record<string, SignalValue> = {};
        
        // Handle different response formats
        if (Array.isArray(data) && data.length > 0 && 'signals' in data[0]) {
          // New format: array of connections with nested signals
          console.log('Processing new format: connections with nested signals');
          data.forEach((connection: any) => {
            if (connection.signals && Array.isArray(connection.signals)) {
              connection.signals.forEach((signal: any) => {
                initialSignals[signal.name] = {
                  value: signal.value,
                  timestamp: Date.now()
                };
              });
            }
          });
          
          setSignals(initialSignals);
          console.log(`✅ Loaded ${Object.keys(initialSignals).length} signals from PLC Bridge API (new format)`);
        }
        else if (data.message && Array.isArray(data.message)) {
          // Check if it's connections with signals
          if (data.message.length > 0 && 'signals' in data.message[0]) {
            // Format: connections with nested signals in message property
            console.log('Processing format: connections with nested signals in message property');
            data.message.forEach((connection: any) => {
              if (connection.signals && Array.isArray(connection.signals)) {
                connection.signals.forEach((signal: any) => {
                  initialSignals[signal.name] = {
                    value: signal.value,
                    timestamp: Date.now()
                  };
                });
              }
            });
          }
          // Legacy format: flat list of signals
          else if (data.message.length > 0 && 'name' in data.message[0] && 'value' in data.message[0]) {
            console.log('Processing legacy format: flat list of signals');
            data.message.forEach((signal: any) => {
              initialSignals[signal.name] = {
                value: signal.value,
                timestamp: Date.now()
              };
            });
          }
          
          setSignals(initialSignals);
          console.log(`✅ Loaded ${Object.keys(initialSignals).length} signals from PLC Bridge API`);
        } else {
          throw new Error('Invalid response format from PLC Bridge API');
        }
      })
      .catch(error => {
        console.error('❌ Error loading signals from PLC Bridge API:', error);
        console.log('Falling back to warehouse dashboard API...');
        
        // Fallback to the warehouse dashboard API
        fetch('/api/method/epibus.www.warehouse_dashboard.get_modbus_data')
          .then(response => response.json())
          .then(data => {
            const fallbackSignals: Record<string, SignalValue> = {};
            
            if (data.message && Array.isArray(data.message)) {
              // Process connections and their signals
              data.message.forEach((connection: any) => {
                if (connection.signals && Array.isArray(connection.signals)) {
                  connection.signals.forEach((signal: any) => {
                    fallbackSignals[signal.name] = {
                      value: signal.value,
                      timestamp: Date.now()
                    };
                  });
                }
              });
              
              setSignals(fallbackSignals);
              console.log(`✅ Loaded ${Object.keys(fallbackSignals).length} signals from fallback API`);
            } else {
              console.error('❌ Invalid response format from fallback API');
            }
          })
          .catch(fallbackError => {
            console.error('❌ Error loading signals from fallback API:', fallbackError);
          });
      });
  }, []);

  return {
    signals,
    writeSignal,
    connected
  };
}
