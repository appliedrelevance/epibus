import React from 'react';
import { useSignalMonitor } from '../hooks/useSignalMonitor';

interface PLCStatusProps {
  className?: string;
}

export const PLCStatus: React.FC<PLCStatusProps> = ({ className = '' }) => {
  const { signals, connected } = useSignalMonitor();
  
  // Check if PLC cycle is running
  const cycleRunning = signals['WAREHOUSE-ROBOT-1-CYCLE_RUNNING']?.value === true;
  
  // Check for error state
  const errorState = signals['WAREHOUSE-ROBOT-1-PICK_ERROR']?.value === true;
  
  return (
    <div className={`plc-status ${className}`}>
      <div className="flex flex-col gap-2 p-4 bg-white rounded-lg shadow">
        <h3 className="text-lg font-semibold">PLC Status</h3>
        
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span>{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${cycleRunning ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          <span>PLC Cycle {cycleRunning ? 'Running' : 'Stopped'}</span>
        </div>
        
        {errorState && (
          <div className="flex items-center gap-2 text-red-600">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span>Error Detected</span>
          </div>
        )}
      </div>
    </div>
  );
};
