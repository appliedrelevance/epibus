import { useState, useEffect } from 'react';
import { ModbusConnection } from '../App';
import Filters from './Filters';
import LoadingIndicator from './LoadingIndicator';
import ErrorMessage from './ErrorMessage';
import ConnectionCard from './ConnectionCard';
import ConnectionStatusIndicator from './ConnectionStatusIndicator';
import { EventLog } from './EventLog';
import { PLCStatus } from './PLCStatus';
import { useSignalMonitorContext } from '../contexts/SignalMonitorContext';
import { clearAllSortPreferences } from '../utils/storageUtils';
import './ModbusDashboard.css';

interface ModbusDashboardProps {
  connections: ModbusConnection[];
  loading: boolean;
  error: string | null;
}

const ModbusDashboard: React.FC<ModbusDashboardProps> = ({
  connections,
  loading,
  error
}) => {
  const { connected, connectionStatus } = useSignalMonitorContext();
  const [activeFilters, setActiveFilters] = useState({
    deviceType: '',
    signalType: ''
  });
  const [filteredConnections, setFilteredConnections] = useState<ModbusConnection[]>([]);
  
  // Update page title
  useEffect(() => {
    document.title = `Warehouse Dashboard`;
    return () => {
      document.title = 'Frappe';
    };
  }, []);
  
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
  
  // Reset all sorting preferences
  const handleResetSorting = () => {
    clearAllSortPreferences();
    
    // Show feedback to the user
    const toast = document.createElement('div');
    toast.className = 'alert alert-success alert-dismissible fade show position-fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '1050';
    toast.innerHTML = `
      <strong>Success!</strong> Sorting preferences have been reset.
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(toast);
    
    // Remove the toast after 3 seconds
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 150);
    }, 3000);
  };
  
  return (
    <div className="container-fluid">
      <div className="row mt-4 mb-4">
        <div className="col">
          <h1>Warehouse Dashboard</h1>
        </div>
        <div className="col-auto">
          <div className="d-flex gap-2">
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={handleResetSorting}
              title="Reset all table sorting preferences"
            >
              <i className="fa fa-sort"></i> Reset Sorting
            </button>
          </div>
        </div>
      </div>
      
      {/* Connection Status Indicator will be shown below */}
      
      {/* Connection Status Indicator */}
      <ConnectionStatusIndicator
        connected={connected}
        lastUpdateTime={connectionStatus?.timestamp ? connectionStatus.timestamp * 1000 : undefined}
      />
      
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
        {/* No data message */}
        {!loading && filteredConnections.length === 0 && (
          <div className="col-12 text-center p-5">
            <h4>No connections match the current filters</h4>
          </div>
        )}
        
        {/* Connection cards */}
        {filteredConnections.map(connection => (
          <ConnectionCard
            key={connection.name} // Use stable key to prevent re-mounting and state loss
            connection={connection}
            activeFilters={activeFilters}
          />
        ))}
      </div>
      
      {/* Event Log Row - Full Width at Bottom */}
      <div className="row mt-4">
        <div className="col-12">
          <EventLog className="h-100" maxHeight="300px" />
        </div>
      </div>
    </div>
  );
};

export default ModbusDashboard;