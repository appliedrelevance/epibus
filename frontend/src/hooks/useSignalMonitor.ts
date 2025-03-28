import { useState, useEffect, useCallback, useRef } from 'react';
import { useEventSource } from './useEventSource';

interface SignalValue {
  value: boolean | number | string;
  timestamp: number;
  source?: string;
}

interface SignalUpdate {
  name: string;
  signal_name: string;
  value: boolean | number | string;
  timestamp: number;
  source: string;
}

interface StatusUpdate {
  connected: boolean;
  connections: Array<{
    name: string;
    connected: boolean;
    last_error: string | null;
  }>;
  timestamp: number;
}

export function useSignalMonitor() {
  const [signals, setSignals] = useState<Record<string, SignalValue>>({});
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<StatusUpdate | null>(null);
  
  // Unified signal update function with priority handling
  const updateSignal = useCallback((signal: string, value: any, source = 'sse', timestamp = Date.now()) => {
    setSignals(prev => {
      // Skip if we have a higher priority recent update
      const current = prev[signal];
      const priority = { verification: 3, plc_bridge_write: 2, sse: 1, write_request: 0 };
      if (current && 
          (priority[current.source as keyof typeof priority] || -1) > (priority[source as keyof typeof priority] || -1) &&
          current.timestamp > timestamp - 3000) {
        return prev;
      }
      
      // Update signal and dispatch local event
      const newValue = { value, timestamp, source };
      window.dispatchEvent(new CustomEvent('local-signal-update', { 
        detail: { signal, value, timestamp, source } 
      }));
      
      return { ...prev, [signal]: newValue };
    });
  }, []);
  
  // Event handlers for SSE
  const eventHandlers = {
    signal_update: (data: SignalUpdate) => {
      if (data?.name) {
        updateSignal(data.name, data.value, data.source, data.timestamp * 1000);
      }
    },
    status_update: (data: StatusUpdate) => {
      setConnected(data.connected);
      setConnectionStatus(data);
    },
    heartbeat: () => {
      // Keep connection alive
    },
    error: (data: any) => {
      console.error('PLC Bridge error:', data);
    }
  };
  
  // Connect to SSE
  const { connected: sseConnected } = useEventSource('http://localhost:7654/events', {
    onOpen: () => console.log('Connected to PLC Bridge SSE'),
    onError: (error) => console.error('PLC Bridge SSE error:', error),
    eventHandlers
  });
  
  // Update connected state based on SSE connection
  useEffect(() => {
    setConnected(sseConnected);
  }, [sseConnected]);
  
  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const response = await fetch('http://localhost:7654/signals');
        const data = await response.json();
        
        if (data.signals) {
          const initialSignals: Record<string, SignalValue> = {};
          
          data.signals.forEach((signal: SignalUpdate) => {
            initialSignals[signal.name] = {
              value: signal.value,
              timestamp: Date.now(),
              source: 'initial_load'
            };
          });
          
          setSignals(initialSignals);
        }
      } catch (error) {
        console.error('Failed to load initial signals:', error);
      }
    };
    
    loadInitialData();
  }, []);
  
  // Write signal function
  const writeSignal = useCallback((signalName: string, value: boolean | number) => {
    // Optimistic update
    updateSignal(signalName, value, 'write_request');
    
    // Send to PLC Bridge
    return fetch('http://localhost:7654/write_signal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ signal_id: signalName, value })
    })
    .then(response => response.json())
    .then(data => data.success)
    .catch(error => {
      console.error('Error updating signal:', error);
      return false;
    });
  }, [updateSignal]);
  
  return { signals, writeSignal, connected, connectionStatus };
}