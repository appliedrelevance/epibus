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
  
  // Update handlers if they change
  useEffect(() => {
    handlersRef.current = options.eventHandlers || {};
  }, [options.eventHandlers]);
  
  // Connect to event source
  useEffect(() => {
    let retryCount = 0;
    const maxRetries = 5;
    const retryDelay = 1000; // 1 second
    
    const createEventSource = () => {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;
      
      eventSource.onopen = () => {
        setConnected(true);
        retryCount = 0; // Reset retry count on successful connection
        options.onOpen?.();
      };
      
      eventSource.onerror = (error) => {
        // Only set disconnected if we're not going to retry
        if (retryCount >= maxRetries) {
          setConnected(false);
          options.onError?.(error);
        } else {
          // Try to reconnect
          retryCount++;
          setTimeout(() => {
            eventSource.close();
            createEventSource();
          }, retryDelay);
        }
      };
      
      return eventSource;
    };
    
    const eventSource = createEventSource();
    
    // Set up event listeners
    const setupEventListeners = () => {
      // Default message handler
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handlersRef.current['message']?.(data);
        } catch (error) {
          console.error('Error parsing event data:', error);
        }
      };
      
      // Add handlers for specific events
      if (handlersRef.current) {
        Object.entries(handlersRef.current).forEach(([eventName, handler]) => {
          if (eventName !== 'message') {
            eventSource.addEventListener(eventName, (event: MessageEvent) => {
              // Only process non-heartbeat events to reduce console noise
              if (eventName !== 'heartbeat') {
                try {
                  const data = JSON.parse(event.data);
                  handler(data);
                } catch (error) {
                  console.error(`Error parsing ${eventName} event data:`, error);
                }
              }
            });
          }
        });
      }
    };
    
    setupEventListeners();
    
    // Cleanup
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setConnected(false);
    };
  }, [url, options.onOpen, options.onError]);
  
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