import { useState, useEffect, useCallback, useRef } from 'react';

interface EventSourceOptions {
  onOpen?: () => void;
  onError?: (error: Event) => void;
  eventHandlers?: Record<string, (data: any) => void>;
}

export function useEventSource(url: string, options: EventSourceOptions = {}) {
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const handlersRef = useRef(options.eventHandlers || {});
  
  // Throttling mechanism
  const lastEventTimeRef = useRef<Record<string, number>>({});
  const throttleIntervalRef = useRef<Record<string, number>>({
    // Default throttle intervals for different event types (in ms)
    signal_update: 500,      // Max 2 updates per second (increased from 100ms)
    signal_updates_batch: 500, // Max 2 batches per second (increased from 100ms)
    status_update: 2000,     // Max 1 status update every 2 seconds (increased from 1000ms)
    heartbeat: 10000,        // Max 1 heartbeat every 10 seconds (increased from 5000ms)
    event_log: 1000,         // Max 1 event log per second (increased from 200ms)
    error: 1000,             // Max 1 error event per second (increased from 500ms)
    default: 500             // Default for other event types (increased from 100ms)
  });
  
  // Event counter for debugging
  const eventCountRef = useRef<Record<string, number>>({});
  const lastLogTimeRef = useRef(Date.now());
  
  // Update handlers if they change
  useEffect(() => {
    handlersRef.current = options.eventHandlers || {};
  }, [options.eventHandlers]);
  
  // Connect to event source
  useEffect(() => {
    let retryCount = 0;
    const maxRetries = 5;
    const maxTotalRetries = 20; // Maximum total retries before giving up completely
    let totalRetries = 0;
    const retryDelay = 2000; // 2 seconds
    const maxRetryDelay = 30000; // 30 seconds maximum delay
    let reconnectTimer: number | null = null;
    let connectionHealthTimer: number | null = null;
    let lastEventTime = Date.now();
    const connectionTimeout = 15000; // 15 seconds without events = stale connection
    
    // Reset counters
    eventCountRef.current = {};
    lastLogTimeRef.current = Date.now();
    
    // No need for event stats logging in production
    const statsInterval = setInterval(() => {
      // Reset counters silently
      eventCountRef.current = {};
      lastLogTimeRef.current = Date.now();
    }, 5000);
    
    // Check connection health periodically
    const checkConnectionHealth = () => {
      const now = Date.now();
      const timeSinceLastEvent = now - lastEventTime;
      
      // If we haven't received any events (including heartbeats) for too long,
      // the connection is probably stale
      if (timeSinceLastEvent > connectionTimeout && eventSourceRef.current) {
        // Force reconnection
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        
        setConnected(false);
        
        // Reconnect after a short delay
        if (reconnectTimer) window.clearTimeout(reconnectTimer);
        reconnectTimer = window.setTimeout(() => {
          createEventSource();
        }, retryDelay);
      }
    };
    
    // Start connection health check
    connectionHealthTimer = window.setInterval(checkConnectionHealth, 5000);
    
    const createEventSource = () => {
      // Close any existing connection first
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      
      try {
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;
        
        // Update last event time on any activity
        lastEventTime = Date.now();
        
        eventSource.onopen = () => {
          setConnected(true);
          retryCount = 0; // Reset retry count on successful connection
          lastEventTime = Date.now(); // Reset timer
          options.onOpen?.();
        };
        
        eventSource.onerror = (error) => {
          totalRetries++;
          
          // Give up completely after too many total retries
          if (totalRetries >= maxTotalRetries) {
            setConnected(false);
            options.onError?.(error);
            return; // Don't retry anymore
          }
          
          // Only set disconnected if we're not going to retry this session
          if (retryCount >= maxRetries) {
            setConnected(false);
            options.onError?.(error);
            
            // Try again after a much longer delay
            if (reconnectTimer) window.clearTimeout(reconnectTimer);
            reconnectTimer = window.setTimeout(() => {
              retryCount = 0; // Reset session retry count
              createEventSource();
            }, maxRetryDelay); // Use maximum delay
          } else {
            // Try to reconnect
            retryCount++;
            
            // Close the current connection
            eventSource.close();
            eventSourceRef.current = null;
            
            // Reconnect after a delay with exponential backoff
            const delay = Math.min(retryDelay * Math.pow(1.5, retryCount), maxRetryDelay);
            
            if (reconnectTimer) window.clearTimeout(reconnectTimer);
            reconnectTimer = window.setTimeout(() => {
              createEventSource();
            }, delay);
          }
        };
        
        return eventSource;
      } catch (error) {
        setConnected(false);
        totalRetries++;
        
        // Give up completely after too many total retries
        if (totalRetries >= maxTotalRetries) {
          return null;
        }
        
        // Try again after a delay with exponential backoff
        const delay = Math.min(retryDelay * Math.pow(1.5, retryCount), maxRetryDelay);
        
        if (reconnectTimer) window.clearTimeout(reconnectTimer);
        reconnectTimer = window.setTimeout(() => {
          createEventSource();
        }, delay);
        
        return null;
      }
    };
    
    const eventSource = createEventSource();
    
    // Set up event listeners with throttling
    const setupEventListeners = () => {
      // Process event with throttling and minimal logging
      const processEvent = (eventName: string, event: MessageEvent) => {
        // Update last event time on any activity
        lastEventTime = Date.now();
        
        // Skip empty events
        if (!event.data || event.data.length === 0) {
          console.warn(`Received empty ${eventName} event, skipping`);
          return;
        }
        
        // Count event for stats
        eventCountRef.current[eventName] = (eventCountRef.current[eventName] || 0) + 1;
        
        // Skip heartbeat events
        if (eventName === 'heartbeat') {
          return;
        }
        
        // Apply throttling
        const now = Date.now();
        const lastTime = lastEventTimeRef.current[eventName] || 0;
        const throttleInterval = throttleIntervalRef.current[eventName] || throttleIntervalRef.current.default;
        
        if (now - lastTime < throttleInterval) {
          // Skip this event due to throttling (no logging needed)
          return;
        }
        
        // Update last event time
        lastEventTimeRef.current[eventName] = now;
        
        // Process the event
        try {
          // Only log non-heartbeat events
          if (eventName !== 'heartbeat') {
            console.log(`🔄 SSE: Received ${eventName} event`);
          }
          
          const data = JSON.parse(event.data);
          
          if (handlersRef.current[eventName]) {
            handlersRef.current[eventName](data);
          } else {
            console.warn(`No handler found for ${eventName} event`);
          }
        } catch (error) {
          console.error(`Error parsing ${eventName} event data:`, error);
          console.error(`Raw event data: ${event.data}`);
        }
      };
      
      // Only set up listeners if we have a valid EventSource
      if (eventSource) {
        // Default message handler
        eventSource.onmessage = (event) => {
          processEvent('message', event);
        };
        
        // Add handlers for specific events
        if (handlersRef.current) {
          Object.entries(handlersRef.current).forEach(([eventName, _handler]) => {
            if (eventName !== 'message') {
              eventSource.addEventListener(eventName, (event: MessageEvent) => {
                processEvent(eventName, event);
              });
            }
          });
        }
      }
    };
    
    if (eventSource) {
      setupEventListeners();
    }
    
    // Cleanup
    return () => {
      // Clear all timers
      clearInterval(statsInterval);
      if (connectionHealthTimer) clearInterval(connectionHealthTimer);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      
      // Close connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setConnected(false);
    };
  }, [url]);
  
  // Method to manually close the connection
  const close = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnected(false);
    }
  }, []);
  
  return { connected, close };
}