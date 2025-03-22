import { useState, useEffect } from 'react';
import { ModbusConnection } from '../App';
import Filters from './Filters';
import PollIndicator from './PollIndicator';
import LoadingIndicator from './LoadingIndicator';
import ErrorMessage from './ErrorMessage';
import ConnectionCard from './ConnectionCard';
import './ModbusDashboard.css';

interface ModbusDashboardProps {
  connections: ModbusConnection[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

const ModbusDashboard: React.FC<ModbusDashboardProps> = ({
  connections,
  loading,
  error,
  onRefresh
}) => {
  const [pollCount, setPollCount] = useState<number>(0);
  const [activeFilters, setActiveFilters] = useState({
    deviceType: '',
    signalType: ''
  });
  const [filteredConnections, setFilteredConnections] = useState<ModbusConnection[]>([]);
  
  // Set up polling interval
  useEffect(() => {
    const pollInterval = 2000; // ms
    const intervalId = setInterval(() => {
      setPollCount(prevCount => prevCount + 1);
      // Update page title to show poll count
      document.title = `Modbus Dashboard (Poll: ${pollCount + 1})`;
    }, pollInterval);
    
    return () => clearInterval(intervalId);
  }, [pollCount]);
  
  // Filter connections when connections or filters change
  useEffect(() => {
    const filtered = connections.filter(conn => {
      // Filter by device type
      if (activeFilters.deviceType && conn.device_type !== activeFilters.deviceType) {
        return false;
      }
      
      // If signal type filter is active, check if connection has any signals of that type
      if (activeFilters.signalType && conn.signals) {
        const hasMatchingSignal = conn.signals.some(
          signal => signal.signal_type === activeFilters.signalType
        );
        if (!hasMatchingSignal) {
          return false;
        }
      }
      
      return true;
    });
    
    setFilteredConnections(filtered);
  }, [connections, activeFilters]);
  
  // Handle filter changes
  const handleFilterChange = (filterType: 'deviceType' | 'signalType', value: string) => {
    setActiveFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
  };
  
  return (
    <div className="container-fluid">
      <div className="row mt-4 mb-4">
        <div className="col">
          <h1>Warehouse Dashboard</h1>
        </div>
        <div className="col-auto">
          <div className="btn-group" role="group">
            <button 
              type="button" 
              className="btn btn-outline-primary" 
              onClick={onRefresh}
              disabled={loading}
            >
              <i className="fa fa-refresh"></i> Refresh
            </button>
          </div>
        </div>
      </div>
      
      {/* Loading indicator */}
      {loading && <LoadingIndicator />}
      
      {/* Error message */}
      {error && <ErrorMessage message={error} />}
      
      {/* Filters */}
      <Filters 
        activeFilters={activeFilters}
        onFilterChange={handleFilterChange}
      />
      
      <div id="dashboard-grid" className="row">
        {/* Poll indicator */}
        <PollIndicator 
          pollCount={pollCount} 
          pollInterval={2000}
        />
        
        {/* No data message */}
        {!loading && filteredConnections.length === 0 && (
          <div className="col-12 text-center p-5">
            <h4>No connections match the current filters</h4>
          </div>
        )}
        
        {/* Connection cards */}
        {filteredConnections.map(connection => (
          <ConnectionCard 
            key={connection.name}
            connection={connection}
            activeFilters={activeFilters}
          />
        ))}
      </div>
    </div>
  );
};

export default ModbusDashboard;