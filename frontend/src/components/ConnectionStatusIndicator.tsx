import React from 'react';
import './ConnectionStatusIndicator.css';

interface ConnectionStatusIndicatorProps {
  connected: boolean;
  lastUpdateTime?: number;
}

const ConnectionStatusIndicator: React.FC<ConnectionStatusIndicatorProps> = ({
  connected,
  lastUpdateTime
}) => {
  const formattedTime = lastUpdateTime 
    ? new Date(lastUpdateTime).toLocaleTimeString() 
    : 'Never';

  return (
    <div className="connection-status-indicator">
      <div className="d-flex align-items-center">
        <div className={`status-dot ${connected ? 'connected' : 'disconnected'}`}></div>
        <div className="status-text">
          <span className="status-label">
            {connected ? 'Connected to PLC Bridge' : 'Disconnected from PLC Bridge'}
          </span>
          <span className="status-time">
            Last update: {formattedTime}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ConnectionStatusIndicator;