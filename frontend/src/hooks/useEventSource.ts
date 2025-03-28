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
    
    // Log event stats periodically
    const statsInterval = setInterval(() => {
      const now = Date.now();
      const elapsed = (now - lastLogTimeRef.current) / 1000;
      
      if (Object.keys(eventCountRef.current).length > 0) {
        console.log(`SSE Events in last ${elapsed.toFixed(1)}s:`, { ...eventCountRef.current });
      }
      
      // Reset counters
      eventCountRef.current = {};
      lastLogTimeRef.current = now;
    }, 5000);
    
    // Check connection health periodically
    const checkConnectionHealth = () => {
      const now = Date.now();
      const timeSinceLastEvent = now - lastEventTime;
      
      // If we haven't received any events (including heartbeats) for too long,
      // the connection is probably stale
      if (timeSinceLastEvent > connectionTimeout && eventSourceRef.current) {
        console.warn(`Connection appears stale (${(timeSinceLastEvent/1000).toFixed(1)}s since last event). Reconnecting...`);
        
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
      console.log(`Creating EventSource connection to ${url}`);
      
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
          console.log('EventSource connection opened');
          setConnected(true);
          retryCount = 0; // Reset retry count on successful connection
          lastEventTime = Date.now(); // Reset timer
          options.onOpen?.();
        };
        
        eventSource.onerror = (error) => {
          console.error('EventSource error:', error);
          totalRetries++;
          
          // Give up completely after too many total retries
          if (totalRetries >= maxTotalRetries) {
            console.error(`Giving up after ${totalRetries} total connection attempts. SSE server appears to be unavailable.`);
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
            console.log(`Retrying EventSource connection (attempt ${retryCount}/${maxRetries}, total: ${totalRetries}/${maxTotalRetries})...`);
            
            // Close the current connection
            eventSource.close();
            eventSourceRef.current = null;
            
            // Reconnect after a delay with exponential backoff
            const delay = Math.min(retryDelay * Math.pow(1.5, retryCount), maxRetryDelay);
            console.log(`Will retry in ${delay/1000} seconds`);
            
            if (reconnectTimer) window.clearTimeout(reconnectTimer);
            reconnectTimer = window.setTimeout(() => {
              createEventSource();
            }, delay);
          }
        };
        
        return eventSource;
      } catch (error) {
        console.error('Error creating EventSource:', error);
        setConnected(false);
        totalRetries++;
        
        // Give up completely after too many total retries
        if (totalRetries >= maxTotalRetries) {
          console.error(`Giving up after ${totalRetries} total connection attempts. SSE server appears to be unavailable.`);
          return null;
        }
        
        // Try again after a delay with exponential backoff
        const delay = Math.min(retryDelay * Math.pow(1.5, retryCount), maxRetryDelay);
        console.log(`Error creating EventSource. Will retry in ${delay/1000} seconds (total attempts: ${totalRetries}/${maxTotalRetries})`);
        
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
      // Process event with throttling and detailed debugging
      const processEvent = (eventName: string, event: MessageEvent) => {
        // Update last event time on any activity
        lastEventTime = Date.now();
        
        // Log all events for debugging
        console.log(`[DEBUG] Received ${eventName} event:`, {
          eventName,
          data: event.data,
          dataLength: event.data?.length || 0,
          eventType: event.type,
          eventTarget: event.target,
          eventCurrentTarget: event.currentTarget,
          eventOrigin: event.origin,
          eventSource: event.source,
          eventPorts: event.ports,
          eventLastEventId: event.lastEventId,
          eventTimestamp: new Date().toISOString(),
          url: url
        });
        
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
          // Skip this event due to throttling
          console.log(`[DEBUG] Throttling ${eventName} event (last: ${lastTime}, now: ${now}, interval: ${throttleInterval})`);
          return;
        }
        
        // Update last event time
        lastEventTimeRef.current[eventName] = now;
        
        // Process the event
        try {
          console.log(`[DEBUG] Processing ${eventName} event data:`, event.data);
          const data = JSON.parse(event.data);
          console.log(`[DEBUG] Parsed ${eventName} event data:`, data);
          handlersRef.current[eventName]?.(data);
        } catch (error) {
          console.error(`Error parsing ${eventName} event data:`, error);
        }
      };
      
      // Only set up listeners if we have a valid EventSource
      if (eventSource) {
        // Default message handler with debugging
        console.log(`[DEBUG] Setting up onmessage handler for EventSource at ${url}`);
        eventSource.onmessage = (event) => {
          console.log(`[DEBUG] onmessage event received from ${url}`);
          processEvent('message', event);
        };
        
        // Add handlers for specific events with debugging
        if (handlersRef.current) {
          console.log(`[DEBUG] Setting up event handlers for EventSource at ${url}:`, Object.keys(handlersRef.current));
          Object.entries(handlersRef.current).forEach(([eventName, _handler]) => {
            if (eventName !== 'message') {
              console.log(`[DEBUG] Adding event listener for ${eventName} on EventSource at ${url}`);
              eventSource.addEventListener(eventName, (event: MessageEvent) => {
                console.log(`[DEBUG] ${eventName} event received from ${url}`);
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
        console.log('Closing EventSource connection');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setConnected(false);
    };
  }, [url]);
  
  // Method to manually close the connection
  const close = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('Manually closing EventSource connection');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnected(false);
    }
  }, []);
  
  return { connected, close };
}