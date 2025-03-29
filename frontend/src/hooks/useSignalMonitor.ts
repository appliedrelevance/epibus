import { useState, useEffect, useCallback } from 'react';
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
  
  // Simplified signal update function with cleaner priority handling
  const updateSignal = useCallback((signal: string, value: any, source = 'sse', timestamp = Date.now()) => {
    // Only log when an event is sent or received
    if (source === 'plc_bridge') {
      console.log(`🔄 Signal update from PLC Bridge: ${signal} - value:`, value);
    }
    
    setSignals(prev => {
      const current = prev[signal];
      
      // Simplified priority system - clear hierarchy with fewer levels
      const priorities = { verification: 3, plc_bridge: 2, sse: 1, write_request: 0 };
      const currentPriority = current?.source ? (priorities[current.source as keyof typeof priorities] ?? -1) : -1;
      const newPriority = priorities[source as keyof typeof priorities] ?? -1;
      
      // Only skip updates from lower priority sources if the current value is recent
      // IMPORTANT: Always accept updates from plc_bridge regardless of priority
      if (current &&
          currentPriority > newPriority &&
          current.timestamp > timestamp - 3000 &&
          source !== 'plc_bridge') { // Never skip plc_bridge updates
        return prev;
      }
      
      // Update signal and dispatch local event
      const newValue = { value, timestamp, source };
      
      // Only dispatch event if value actually changed
      if (!current || current.value !== value) {
        console.log(`🔍 DEBUG: Dispatching event for ${signal} - value changed from`,
                    current?.value, 'to', value);
        window.dispatchEvent(new CustomEvent('local-signal-update', {
          detail: { signal, value, timestamp, source }
        }));
      } else {
        console.log(`🔍 DEBUG: Not dispatching event for ${signal} - value unchanged`);
      }
      
      return { ...prev, [signal]: newValue };
    });
  }, []);
  
  // Unified handler for both single and batch signal updates
  const handleSignalUpdates = useCallback((updates: SignalUpdate | SignalUpdate[]) => {
    // Convert single update to array for unified processing
    const updatesArray = Array.isArray(updates) ? updates : [updates];
    
    // Only log when events are received
    console.log(`🔄 Received ${updatesArray.length} signal updates`);
    
    // Process all updates in a single state update for better performance
    setSignals(prev => {
      const newSignals = { ...prev };
      
      updatesArray.forEach(update => {
        // Use signal_name if available, otherwise fall back to name
        const signalId = update?.name;
        const signalName = update?.signal_name || signalId;
        
        if (!signalId) {
          console.warn('⚠️ Skipping update with no ID:', update);
          return;
        }
        
        // Use the source from the event or default to 'plc_bridge'
        const source = update.source || 'plc_bridge';
        const timestamp = update.timestamp * 1000;
        
        const current = prev[signalId];
        
        // For plc_bridge updates, always update the value
        if (source === 'plc_bridge') {
          // Create new value object
          const newValue = {
            value: update.value,
            timestamp,
            source
          };
          
          // Store in the new signals object
          newSignals[signalId] = newValue;
          
          // Dispatch local event for UI updates
          console.log(`🔄 PLC Bridge update: ${signalName} = ${update.value}`);
          window.dispatchEvent(new CustomEvent('local-signal-update', {
            detail: { signal: signalId, value: update.value, timestamp, source, signalName }
          }));
        } else {
          // For other sources, use the priority system via updateSignal
          // Create new value object
          const newValue = {
            value: update.value,
            timestamp,
            source
          };
          
          // Store in the new signals object
          newSignals[signalId] = newValue;
          
          // Dispatch local event only if value changed
          if (!current || current.value !== update.value) {
            console.log(`🔄 Value changed: ${signalName} from ${current?.value} to ${update.value}`);
            window.dispatchEvent(new CustomEvent('local-signal-update', {
              detail: { signal: signalId, value: update.value, timestamp, source, signalName }
            }));
          }
        }
      });
      
      return newSignals;
    });
  }, []);
  
  // Simplified event handlers with unified signal update handling
  const eventHandlers = {
    signal_update: (data: SignalUpdate) => {
      const signalName = data?.signal_name || data?.name || 'unknown';
      console.log(`🔄 Received signal update: ${signalName}`);
      
      if (data?.name) {
        // Ensure source is set to plc_bridge for direct signal updates
        if (!data.source) {
          data.source = 'plc_bridge';
        }
        handleSignalUpdates(data);
      } else {
        console.warn('⚠️ Ignoring signal update with no ID');
      }
    },
    signal_updates_batch: (data: { updates: SignalUpdate[] }) => {
      const updateCount = data?.updates?.length || 0;
      console.log(`🔄 Received batch update with ${updateCount} signals`);
      
      if (data?.updates && Array.isArray(data.updates)) {
        // Ensure source is set to plc_bridge for all updates in the batch
        data.updates.forEach(update => {
          if (!update.source) {
            update.source = 'plc_bridge';
          }
        });
        handleSignalUpdates(data.updates);
      } else {
        console.warn('⚠️ Ignoring batch update with invalid data');
      }
    },
    status_update: (data: StatusUpdate) => {
      console.log(`🔄 PLC connection status: ${data.connected ? 'Connected' : 'Disconnected'}`);
      setConnected(data.connected);
      setConnectionStatus(data);
    },
    event_log: (data: any) => {
      console.log(`🔄 Event log: ${data.event_type || 'Unknown event'}`);
      // Dispatch event_log events to be captured by useEventLog
      window.dispatchEvent(new CustomEvent('event-log-update', {
        detail: data
      }));
    },
    heartbeat: () => {
      // Keep connection alive - no logging needed for heartbeats
    },
    error: (data: any) => {
      console.error('❌ PLC Bridge error:', data.message || 'Unknown error');
      
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
        onOpen: () => console.log('Connected to PLC Bridge SSE'),
        onError: (error) => console.error('PLC Bridge SSE error:', error),
        eventHandlers
      })
    : { connected: false }; // Return a dummy value when SSE is disabled
  
  // Update connected state based on SSE connection
  useEffect(() => {
    setConnected(ENABLE_SSE_CONNECTION ? sseConnected : false);
  }, [sseConnected]);
  
  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        if (!ENABLE_SSE_CONNECTION) {
          // Simplified mock data for testing when PLC Bridge is unavailable
          setSignals({
            'mock_signal_1': { value: true, timestamp: Date.now(), source: 'mock' },
            'mock_signal_2': { value: false, timestamp: Date.now(), source: 'mock' },
            'mock_signal_3': { value: 42, timestamp: Date.now(), source: 'mock' }
          });
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
      return new Promise<boolean>(resolve => {
        setTimeout(() => {
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