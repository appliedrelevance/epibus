import { useState, useEffect, useRef } from 'react';
import { ModbusConnection } from '../App';
import Filters from './Filters';
import PollIndicator from './PollIndicator';
import LoadingIndicator from './LoadingIndicator';
import ErrorMessage from './ErrorMessage';
import ConnectionCard from './ConnectionCard';
import { clearAllSortPreferences } from '../utils/storageUtils';
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
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const lastRefreshTime = useRef<number>(Date.now());
  const pollInterval = 30000; // 30 seconds between auto-refreshes
  
  // Set up polling interval for UI updates and potential data refresh
  useEffect(() => {
    const intervalId = setInterval(() => {
      setPollCount(prevCount => prevCount + 1);
      
      // Update page title to show poll count
      document.title = `Modbus Dashboard (Poll: ${pollCount + 1})`;
      
      // Check if we should auto-refresh data
      if (autoRefresh && Date.now() - lastRefreshTime.current >= pollInterval) {
        console.log('Auto-refreshing data due to poll interval');
        onRefresh();
        lastRefreshTime.current = Date.now();
      }
    }, 2000); // UI update every 2 seconds
    
    return () => clearInterval(intervalId);
  }, [pollCount, autoRefresh, onRefresh]);
  
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
  
  // Handle manual refresh
  const handleManualRefresh = () => {
    lastRefreshTime.current = Date.now();
    onRefresh();
  };
  
  // Toggle auto-refresh
  const toggleAutoRefresh = () => {
    setAutoRefresh(prev => !prev);
  };
  
  // Reset all sorting preferences
  const handleResetSorting = () => {
    clearAllSortPreferences();
    // Force a re-render of the component to reflect the reset
    setPollCount(prevCount => prevCount + 1);
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
            <div className="btn-group" role="group">
              <button
                type="button"
                className="btn btn-outline-primary"
                onClick={handleManualRefresh}
                disabled={loading}
              >
                <i className="fa fa-refresh"></i> Refresh
              </button>
              <button
                type="button"
                className={`btn btn-outline-${autoRefresh ? 'success' : 'secondary'}`}
                onClick={toggleAutoRefresh}
              >
                <i className={`fa fa-${autoRefresh ? 'clock-o' : 'pause'}`}></i>
                {autoRefresh ? ' Auto-refresh On' : ' Auto-refresh Off'}
              </button>
            </div>
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
          autoRefresh={autoRefresh}
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
            key={connection.name} // Use stable key to prevent re-mounting and state loss
            connection={connection}
            activeFilters={activeFilters}
            pollCount={pollCount} // Pass as prop instead of using in key
          />
        ))}
      </div>
    </div>
  );
};

export default ModbusDashboard;