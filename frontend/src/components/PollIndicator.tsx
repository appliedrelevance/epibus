import React from 'react';
import './PollIndicator.css';

interface PollIndicatorProps {
  pollCount: number;
  pollInterval: number;
  autoRefresh?: boolean;
}

const PollIndicator: React.FC<PollIndicatorProps> = ({
  pollCount,
  pollInterval,
  autoRefresh = true
}) => {
  return (
    <div id="poll-indicator" className="col-12 mb-4">
      <div className="d-flex justify-content-between align-items-center">
        <div>
          <h5 className="mb-1">Modbus Polling Active</h5>
          <p className="mb-0 text-muted">
            UI updates every {pollInterval / 1000} seconds
            {autoRefresh && <span> • Data auto-refresh enabled</span>}
            {!autoRefresh && <span> • Data auto-refresh disabled</span>}
          </p>
        </div>
        <div id="poll-count-display" className={`badge ${autoRefresh ? 'bg-primary' : 'bg-secondary'} p-2`}>
          Poll count: {pollCount}
        </div>
      </div>
    </div>
  );
};

export default PollIndicator;