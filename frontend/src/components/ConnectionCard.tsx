import React from 'react';
import { ModbusConnection } from '../App';
import SignalTable from './SignalTable';
import './ConnectionCard.css';

interface ConnectionCardProps {
  connection: ModbusConnection;
  activeFilters: {
    deviceType: string;
    signalType: string;
  };
  pollCount?: number; // Optional poll count prop
}

const ConnectionCard: React.FC<ConnectionCardProps> = ({ connection, activeFilters, pollCount }) => {
  // Filter signals based on active filters
  const filteredSignals = React.useMemo(() => {
    // Using useMemo to avoid unnecessary filtering on each render
    return connection.signals.filter(signal => {
      if (activeFilters.signalType && signal.signal_type !== activeFilters.signalType) {
        return false;
      }
      return true;
    });
  }, [connection.signals, activeFilters.signalType, pollCount]); // Re-compute when signals, filters, or pollCount changes

  return (
    <div className="col-12 mb-4">
      <div
        className="card h-100"
        id={`connection-${connection.name}`}
      >
        {/* Card header */}
        <div className="card-header d-flex justify-content-between align-items-center">
          <h5 className="mb-0">{connection.device_name || connection.name}</h5>
          <span className={`badge ${connection.enabled ? 'bg-success' : 'bg-danger'}`}>
            {connection.enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
        
        {/* Card body */}
        <div className="card-body">
          {/* Connection details */}
          <div className="mb-3">
            <p className="mb-1">
              <strong>Type:</strong> {connection.device_type || 'N/A'}
            </p>
            <p className="mb-1">
              <strong>Host:</strong> {connection.host || 'N/A'}
            </p>
            <p className="mb-0">
              <strong>Port:</strong> {connection.port || 'N/A'}
            </p>
          </div>
          
          {/* Signals table */}
          <div className="signals-container mt-3">
            {filteredSignals.length > 0 ? (
              <SignalTable
                signals={filteredSignals}
                connectionId={connection.name}
              />
            ) : (
              <p className="text-center text-muted">
                No signals match the current filters
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConnectionCard;