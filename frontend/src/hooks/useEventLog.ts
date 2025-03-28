import { useState, useEffect, useCallback } from 'react';
import { useEventSource } from './useEventSource';

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
  
  // Event handlers for SSE
  const eventHandlers = {
    event_log: (data: EventLogEntry) => {
      addEvent({
        ...data,
        timestamp: data.timestamp || Date.now()
      });
    }
  };
  
  // Connect to SSE
  useEventSource('http://localhost:7654/events', {
    eventHandlers
  });
  
  // Load initial events
  useEffect(() => {
    const loadInitialEvents = async () => {
      try {
        const response = await fetch('http://localhost:7654/events/history');
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