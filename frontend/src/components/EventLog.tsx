import React, { useState, useEffect } from 'react';
import { useEventLog } from '../hooks/useEventLog';
import './EventLog.css';

interface EventLogProps {
  className?: string;
  maxHeight?: string;
}

// Interface for signal mapping
interface SignalMapping {
  [key: string]: string; // Maps signal ID to signal_name
}

export const EventLog: React.FC<EventLogProps> = ({
  className = '',
  maxHeight = '300px'
}) => {
  const { events, clearEvents } = useEventLog(100);
  const [filter, setFilter] = useState('');
  const [signalMapping, setSignalMapping] = useState<SignalMapping>({});
  
  // Load signal mapping on component mount
  useEffect(() => {
    const fetchSignalMapping = async () => {
      try {
        // Fetch from the warehouse dashboard API
        const response = await fetch('/api/method/epibus.www.warehouse_dashboard.get_modbus_data');
        const data = await response.json();
        
        if (data && data.message && Array.isArray(data.message)) {
          const mapping: SignalMapping = {};
          
          // Create mapping from signal ID to signal_name
          data.message.forEach((connection: any) => {
            if (connection.signals && Array.isArray(connection.signals)) {
              connection.signals.forEach((signal: any) => {
                if (signal.name && signal.signal_name) {
                  mapping[signal.name] = signal.signal_name;
                }
              });
            }
          });
          
          setSignalMapping(mapping);
        }
      } catch (error) {
        console.error('Error fetching signal mapping:', error);
      }
    };
    
    fetchSignalMapping();
  }, []);
  
  // Filter events
  const filteredEvents = events.filter(event => {
    if (!filter) return true;
    
    const searchText = filter.toLowerCase();
    return (
      (event.event_type && event.event_type.toLowerCase().includes(searchText)) ||
      (event.message && event.message.toLowerCase().includes(searchText)) ||
      (event.signal && event.signal.toLowerCase().includes(searchText)) ||
      (event.connection && event.connection.toLowerCase().includes(searchText))
    );
  });
  
  // Format timestamp as relative time
  const formatTime = (timestamp: number) => {
    const now = Date.now() / 1000; // Current time in seconds
    const diff = now - timestamp; // Difference in seconds
    
    // Format as relative time
    if (diff < 60) {
      return 'just now';
    } else if (diff < 3600) {
      const minutes = Math.floor(diff / 60);
      return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
    } else if (diff < 86400) {
      const hours = Math.floor(diff / 3600);
      return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
    } else {
      const days = Math.floor(diff / 86400);
      return `${days} ${days === 1 ? 'day' : 'days'} ago`;
    }
  };
  
  // Get signal name from ID
  const getSignalName = (signalId: string) => {
    return signalMapping[signalId] || signalId;
  };
  
  // Get status color
  const getStatusColor = (status: string) => {
    return status === 'Success' ? 'text-green-500' : 'text-red-500';
  };
  
  // Get event type icon
  const getEventIcon = (type: string) => {
    switch (type) {
      case 'Signal Update':
        return '🔄';
      case 'Action Execution':
        return '▶️';
      case 'Connection Test':
        return '🔌';
      case 'Error':
        return '❌';
      default:
        return '📝';
    }
  };
  
  return (
    <div className={`event-log ${className}`}>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-semibold">Event Log</h3>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Filter events..."
              className="px-2 py-1 border rounded text-sm"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            <button 
              className="px-2 py-1 bg-gray-200 rounded text-sm"
              onClick={clearEvents}
            >
              Clear
            </button>
          </div>
        </div>
        
        <div 
          className="overflow-y-auto"
          style={{ maxHeight }}
        >
          {filteredEvents.length === 0 ? (
            <div className="text-center text-gray-500 py-4">
              No events to display
            </div>
          ) : (
            <ul className="space-y-2">
              {filteredEvents.map(event => (
                <li 
                  key={event.id} 
                  className="border-b border-gray-100 pb-2"
                >
                  <div className="flex items-start">
                    <div className="mr-2">
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium">{event.event_type}</span>
                        <span className="text-gray-500">{formatTime(event.timestamp)}</span>
                      </div>
                      
                      <div className="text-sm">
                        {event.signal && (
                          <span className="mr-2">
                            <span className="text-gray-500">Signal:</span> {getSignalName(event.signal)}
                          </span>
                        )}
                        
                        {event.new_value && (
                          <span className="mr-2">
                            <span className="text-gray-500">Value:</span> {event.new_value}
                          </span>
                        )}
                        
                        <span className={getStatusColor(event.status)}>
                          {event.status}
                        </span>
                      </div>
                      
                      {event.message && (
                        <div className="text-sm text-gray-700 mt-1">
                          {event.message}
                        </div>
                      )}
                      
                      {event.error_message && (
                        <div className="text-sm text-red-600 mt-1">
                          {event.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};