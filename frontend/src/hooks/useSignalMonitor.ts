import { useState, useEffect, useCallback, useRef } from 'react';

interface SignalValue {
  value: boolean | number;
  timestamp: number;
  source?: string;
}

// TypeScript interface for Frappe's global object
declare global {
  interface Window {
    frappe?: {
      realtime: {
        on: (event: string, callback: (data: any) => void) => void;
        off: (event: string, callback?: (data: any) => void) => void;
      };
      socketio?: {
        socket: {
          connected: boolean;
          on: (event: string, callback: () => void) => void;
        }
      };
    };
  }
}

export function useSignalMonitor() {
  const [signals, setSignals] = useState<Record<string, SignalValue>>({});
  const [connected, setConnected] = useState(false);
  const socketReady = useRef(false);
  
  // Unified signal update function with priority handling
  const updateSignal = useCallback((signal: string, value: any, source = 'realtime', timestamp = Date.now()) => {
    setSignals(prev => {
      // Skip if we have a higher priority recent update
      const current = prev[signal];
      const priority = { verification: 3, plc_bridge_write: 2, realtime: 1, write_request: 0 };
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

  // Socket connection and event handling
  useEffect(() => {
    const connectSocket = async () => {
      // Wait for Frappe socket to be available
      while (!window.frappe?.socketio?.socket) {
        await new Promise(r => setTimeout(r, 100));
      }
      
      // Set up event handlers
      const socket = window.frappe.socketio.socket;
      setConnected(socket.connected);
      socket.on('connect', () => setConnected(true));
      socket.on('disconnect', () => setConnected(false));
      
      // Handle signal updates
      window.frappe.realtime.on('modbus_signal_update', (data: any) => {
        if (data?.signal) {
          updateSignal(data.signal, data.value, data.source, data.timestamp);
        }
      });
      
      // Handle PLC status updates
      window.frappe.realtime.on('plc:status', (data: any) => {
        if (data?.connected !== undefined) setConnected(data.connected);
      });
      
      // Request initial status
      fetch('/api/method/epibus.api.plc.get_plc_status').catch(() => {});
      
      // Mark socket as ready and load initial data
      socketReady.current = true;
      loadInitialData();
    };
    
    connectSocket();
    
    return () => {
      if (window.frappe?.realtime) {
        window.frappe.realtime.off('modbus_signal_update');
        window.frappe.realtime.off('plc:status');
      }
    };
  }, [updateSignal]);

  // Load initial signal data - using only the primary API
  const loadInitialData = useCallback(async () => {
    try {
      const response = await fetch('/api/method/epibus.api.plc.get_signals');
      const data = await response.json();
      
      // Extract signals from response
      const extractSignals = (data: any): Record<string, SignalValue> => {
        const result: Record<string, SignalValue> = {};
        
        // Handle connection-based format
        if (Array.isArray(data) && data[0]?.signals) {
          data.forEach((conn: any) => {
            conn.signals?.forEach((signal: any) => {
              result[signal.name] = { 
                value: signal.value, 
                timestamp: Date.now(), 
                source: 'initial_load' 
              };
            });
          });
          return result;
        }
        
        // Handle message wrapper format
        if (data?.message && Array.isArray(data.message)) {
          return extractSignals(data.message);
        }
        
        // Handle flat signal list
        if (Array.isArray(data) && data[0]?.name && 'value' in data[0]) {
          data.forEach((signal: any) => {
            result[signal.name] = { 
              value: signal.value, 
              timestamp: Date.now(), 
              source: 'initial_load' 
            };
          });
          return result;
        }
        
        return result;
      };
      
      const initialSignals = extractSignals(data);
      
      if (Object.keys(initialSignals).length > 0) {
        setSignals(prev => ({ ...prev, ...initialSignals }));
      }
    } catch (error) {
      console.error('Failed to load signals:', error);
    }
  }, []);

  // Write signal function - using only the primary API
  const writeSignal = useCallback((signalName: string, value: boolean | number) => {
    // Optimistic update
    updateSignal(signalName, value, 'write_request');
    
    // Send to server
    return fetch('/api/method/epibus.api.plc.update_signal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': localStorage.getItem('csrf_token') || ''
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

  return { signals, writeSignal, connected };
}