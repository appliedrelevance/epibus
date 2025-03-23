import { useState, useEffect, useCallback } from 'react';
import io from 'socket.io-client';

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
  const [socket, setSocket] = useState<SocketIOClient.Socket | null>(null);
  const [connected, setConnected] = useState(false);

  // Initialize socket connection
  useEffect(() => {
    console.log('🔌 Initializing Frappe socket connection...');
    
    const socket = io('/', {
      path: '/socketio'
    });

    socket.on('connect', () => {
      console.log('✅ Connected to Frappe socket');
      setConnected(true);
      
      // Emit a join event to subscribe to Frappe real-time events
      socket.emit('join', { 
        doctype: '*',
        docname: '*'
      });
    });

    socket.on('disconnect', () => {
      console.log('❌ Disconnected from Frappe socket');
      setConnected(false);
    });

    socket.on('modbus_signal_update', (data: SignalUpdateEvent) => {
      console.log(`🔄 Signal update: ${data.signal} = ${data.value}`);
      setSignals(prev => ({
        ...prev,
        [data.signal]: {
          value: data.value,
          timestamp: data.timestamp
        }
      }));
    });

    setSocket(socket);

    return () => {
      console.log('👋 Closing socket connection');
      socket.close();
    };
  }, []);

  // Function to write a signal value
  const writeSignal = useCallback((signalName: string, value: boolean | number) => {
    console.log(`✏️ Writing signal: ${signalName} = ${value}`);
    
    return fetch('/api/method/epibus.epibus.api.plc.update_signal', {
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
      console.log('Signal write response:', data);
      return data.success;
    })
    .catch(error => {
      console.error('❌ Error writing signal:', error);
      return false;
    });
  }, []);

  // Load initial signals
  useEffect(() => {
    fetch('/api/method/epibus.epibus.api.plc.get_signals')
      .then(response => response.json())
      .then(data => {
        const initialSignals: Record<string, SignalValue> = {};
        
        data.message.forEach((signal: any) => {
          initialSignals[signal.name] = {
            value: signal.value,
            timestamp: Date.now()
          };
        });
        
        setSignals(initialSignals);
        console.log(`✅ Loaded ${Object.keys(initialSignals).length} signals`);
      })
      .catch(error => {
        console.error('❌ Error loading signals:', error);
      });
  }, []);

  return {
    signals,
    writeSignal,
    connected
  };
}
