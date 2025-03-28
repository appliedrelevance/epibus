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
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;
    
    eventSource.onopen = () => {
      setConnected(true);
      options.onOpen?.();
    };
    
    eventSource.onerror = (error) => {
      setConnected(false);
      options.onError?.(error);
    };
    
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
      eventSource.close();
      setConnected(false);
    };
  }, [url, options.onOpen, options.onError]);
  
  // Method to manually close the connection
  const close = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setConnected(false);
    }
  }, []);
  
  return { connected, close };
}