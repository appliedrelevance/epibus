import React, { createContext, useContext, ReactNode } from 'react';
import { useSignalMonitor } from '../hooks/useSignalMonitor';

// Define the context type
interface SignalMonitorContextType {
  signals: Record<string, {
    value: boolean | number | string;
    timestamp: number;
    source?: string;
  }>;
  writeSignal: (signalName: string, value: boolean | number) => Promise<boolean>;
  connected: boolean;
  connectionStatus: {
    connected: boolean;
    connections: Array<{
      name: string;
      connected: boolean;
      last_error: string | null;
    }>;
    timestamp: number;
  } | null;
}

// Create the context with a default value
const SignalMonitorContext = createContext<SignalMonitorContextType | null>(null);

// Provider component
export const SignalMonitorProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Use the hook once at the top level
  const signalMonitor = useSignalMonitor();
  
  return (
    <SignalMonitorContext.Provider value={signalMonitor}>
      {children}
    </SignalMonitorContext.Provider>
  );
};

// Custom hook to use the context
export const useSignalMonitorContext = () => {
  const context = useContext(SignalMonitorContext);
  if (context === null) {
    throw new Error('useSignalMonitorContext must be used within a SignalMonitorProvider');
  }
  return context;
};