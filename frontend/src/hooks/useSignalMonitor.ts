import { useState, useEffect, useCallback, useRef } from 'react';
import { useEventSource } from './useEventSource';
import {
  SSE_EVENTS_ENDPOINT,
  SSE_SIGNALS_ENDPOINT,
  SSE_WRITE_SIGNAL_ENDPOINT,
  ENABLE_SSE_CONNECTION
} from '../config';

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
    signal_updates_batch: (data: { updates: SignalUpdate[] }) => {
      if (data?.updates && Array.isArray(data.updates)) {
        console.log(`Processing batch of ${data.updates.length} signal updates`);
        data.updates.forEach(update => {
          if (update?.name) {
            updateSignal(update.name, update.value, update.source, update.timestamp * 1000);
          }
        });
      }
    },
    status_update: (data: StatusUpdate) => {
      console.log('Received status update:', data);
      setConnected(data.connected);
      setConnectionStatus(data);
    },
    event_log: (data: any) => {
      // Dispatch event_log events to be captured by useEventLog
      window.dispatchEvent(new CustomEvent('event-log-update', {
        detail: data
      }));
    },
    heartbeat: () => {
      // Keep connection alive
    },
    error: (data: any) => {
      console.error('PLC Bridge error:', data);
      // Also dispatch error events to be captured by useEventLog
      window.dispatchEvent(new CustomEvent('event-log-update', {
        detail: {
          event_type: 'Error',
          status: 'Failed',
          message: data.message || 'Unknown error',
          timestamp: Date.now() / 1000
        }
      }));
    }
  };
  
  // Connect to SSE only if enabled
  const { connected: sseConnected } = ENABLE_SSE_CONNECTION
    ? useEventSource(SSE_EVENTS_ENDPOINT, {
        onOpen: () => console.log('Connected to PLC Bridge SSE - Ready to receive updates'),
        onError: (error) => console.error('PLC Bridge SSE error:', error),
        eventHandlers
      })
    : { connected: false }; // Return a dummy value when SSE is disabled
  
  // Update connected state based on SSE connection
  useEffect(() => {
    if (!ENABLE_SSE_CONNECTION) {
      console.warn('PLC Bridge SSE connection is disabled in config. Using mock or fallback data.');
      setConnected(false);
    } else {
      setConnected(sseConnected);
    }
  }, [sseConnected]);
  
  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        if (!ENABLE_SSE_CONNECTION) {
          console.warn('PLC Bridge is disabled. Using mock data for signals.');
          // Create some mock signals for testing when PLC Bridge is unavailable
          const mockSignals: Record<string, SignalValue> = {
            'mock_signal_1': { value: true, timestamp: Date.now(), source: 'mock' },
            'mock_signal_2': { value: false, timestamp: Date.now(), source: 'mock' },
            'mock_signal_3': { value: 42, timestamp: Date.now(), source: 'mock' }
          };
          setSignals(mockSignals);
          return;
        }
        
        // Only try to fetch from the real endpoint if SSE is enabled
        const response = await fetch(SSE_SIGNALS_ENDPOINT);
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
        
        if (ENABLE_SSE_CONNECTION) {
          // If we're trying to use the real PLC Bridge but it failed,
          // suggest disabling it in the config
          console.warn('Consider setting ENABLE_SSE_CONNECTION to false in config.ts if the PLC Bridge is unavailable');
        }
      }
    };
    
    loadInitialData();
  }, []);
  
  // Write signal function
  const writeSignal = useCallback((signalName: string, value: boolean | number) => {
    // Optimistic update
    updateSignal(signalName, value, 'write_request');
    
    // If SSE is disabled, just return a mock success response
    if (!ENABLE_SSE_CONNECTION) {
      console.log('PLC Bridge is disabled. Mock signal write:', { signalName, value });
      // Simulate a successful write with a delay
      return new Promise<boolean>(resolve => {
        setTimeout(() => {
          // Update the signal with a "verification" source to simulate the PLC confirming the change
          updateSignal(signalName, value, 'verification');
          resolve(true);
        }, 500);
      });
    }
    
    // Send to real PLC Bridge
    return fetch(SSE_WRITE_SIGNAL_ENDPOINT, {
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