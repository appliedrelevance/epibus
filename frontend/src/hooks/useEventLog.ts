import { useState, useEffect, useCallback } from 'react';
import { SSE_EVENTS_HISTORY_ENDPOINT } from '../config';

// IMPORTANT: We're no longer importing useEventSource to avoid creating duplicate connections
// Event log entries will now be added via the global event listener

interface EventLogEntry {
  id?: string;
  event_type: string;
  status: 'Success' | 'Failed';
  connection?: string;
  signal?: string;
  action?: string;
  previous_value?: string;
  new_value?: string;
  message?: string;
  error_message?: string;
  timestamp: number;
}

export function useEventLog(maxEvents = 100) {
  const [events, setEvents] = useState<EventLogEntry[]>([]);
  
  // Add event to log
  const addEvent = useCallback((event: EventLogEntry) => {
    setEvents(prev => {
      // Add unique ID if not present
      const newEvent = {
        ...event,
        id: event.id || `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      };
      
      // Add to beginning of array and limit size
      const updated = [newEvent, ...prev].slice(0, maxEvents);
      return updated;
    });
  }, [maxEvents]);
  
  // Set up event listener for event_log events from useSignalMonitor
  useEffect(() => {
    const handleEventLog = (event: Event) => {
      const customEvent = event as CustomEvent<EventLogEntry>;
      if (customEvent.detail) {
        addEvent({
          ...customEvent.detail,
          timestamp: customEvent.detail.timestamp || Date.now()
        });
      }
    };
    
    // Add event listener for event_log events
    window.addEventListener('event-log-update', handleEventLog);
    
    // Clean up event listener when component unmounts
    return () => {
      window.removeEventListener('event-log-update', handleEventLog);
    };
  }, [addEvent]);
  
  // Load initial events
  useEffect(() => {
    const loadInitialEvents = async () => {
      try {
        const response = await fetch(SSE_EVENTS_HISTORY_ENDPOINT);
        const data = await response.json();
        
        if (data.events && Array.isArray(data.events)) {
          setEvents(data.events.slice(0, maxEvents));
        }
      } catch (error) {
        console.error('Failed to load initial events:', error);
      }
    };
    
    loadInitialEvents();
  }, [maxEvents]);
  
  // Clear events
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);
  
  return { events, addEvent, clearEvents };
}