import React from 'react';
import './PollIndicator.css';

interface PollIndicatorProps {
  pollCount: number;
  pollInterval: number;
}

const PollIndicator: React.FC<PollIndicatorProps> = ({ pollCount, pollInterval }) => {
  return (
    <div id="poll-indicator" className="col-12 mb-4">
      <div className="d-flex justify-content-between align-items-center">
        <div>
          <h5 className="mb-1">Modbus Polling Active</h5>
          <p className="mb-0 text-muted">
            Auto-refreshing every {pollInterval / 1000} seconds
          </p>
        </div>
        <div id="poll-count-display" className="badge bg-primary p-2">
          Poll count: {pollCount}
        </div>
      </div>
    </div>
  );
};

export default PollIndicator;