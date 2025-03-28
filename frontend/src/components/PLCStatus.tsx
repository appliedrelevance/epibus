import React from 'react';
import { useSignalMonitorContext } from '../contexts/SignalMonitorContext';

interface PLCStatusProps {
  className?: string;
}

export const PLCStatus: React.FC<PLCStatusProps> = ({ className = '' }) => {
  const { signals, connected, connectionStatus } = useSignalMonitorContext();
  
  // Check if PLC cycle is running
  const cycleRunning = signals['WAREHOUSE-ROBOT-1-CYCLE_RUNNING']?.value === true;
  
  // Check for error state
  const errorState = signals['WAREHOUSE-ROBOT-1-PICK_ERROR']?.value === true;
  
  return (
    <div className={`plc-status ${className}`}>
      <div className="flex flex-col gap-2 p-4 bg-white rounded-lg shadow">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span>{connected ? 'Connected to PLC Bridge' : 'Disconnected from PLC Bridge'}</span>
        </div>
        
        {/* Display connection status for each Modbus connection */}
        {connectionStatus && connectionStatus.connections.map(conn => (
          <div key={conn.name} className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${conn.connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span>{conn.name}: {conn.connected ? 'Connected' : 'Disconnected'}</span>
          </div>
        ))}
        
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
        
        {/* Last update timestamp */}
        {connectionStatus && (
          <div className="text-xs text-gray-500 mt-2">
            Last Update: {new Date(connectionStatus.timestamp * 1000).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
};
