import React, { useState, useEffect, useRef } from 'react';
import { ModbusSignal } from '../App';
import ValueDisplay from './ValueDisplay';
import ActionButtons from './ActionButtons';
import { useSignalMonitorContext } from '../contexts/SignalMonitorContext';
import './SignalRow.css';

interface SignalRowProps {
  signal: ModbusSignal;
}

const SignalRow: React.FC<SignalRowProps> = ({ signal }) => {
  const [isHighlighted, setIsHighlighted] = useState<boolean>(false);
  const [updateSource, setUpdateSource] = useState<string>('');
  const { signals: realtimeSignals } = useSignalMonitorContext();
  
  // Get the real-time value if available, otherwise use the prop value
  const realtimeValue = realtimeSignals[signal.name]?.value;
  const displayValue = realtimeValue !== undefined ? realtimeValue : signal.value;
  
  // Get the update source if available
  const source = realtimeSignals[signal.name]?.source || '';
  
  // Use signal_name for display, fallback to name if not available
  const displayName = signal.signal_name || signal.name;
  
  const previousValue = useRef<any>(displayValue);
  
  // Listen for real-time updates
  useEffect(() => {
    const handleRealTimeUpdate = (event: Event) => {
      const customEvent = event as CustomEvent<{
        signal: string,
        value: any,
        source?: string,
        signalName?: string
      }>;
      
      // Only process events for this signal
      if (customEvent.detail.signal === signal.name) {
        // Set the update source for visual feedback
        setUpdateSource(customEvent.detail.source || 'realtime');
      }
    };
    
    window.addEventListener('local-signal-update', handleRealTimeUpdate);
    return () => {
      window.removeEventListener('local-signal-update', handleRealTimeUpdate);
    };
  }, [signal.name]);
  
  // Highlight the row when the value changes
  useEffect(() => {
    // Only highlight if the value has actually changed
    if (previousValue.current !== displayValue) {
      setIsHighlighted(true);
      
      // Update the source for visual feedback
      setUpdateSource(source);
      
      const timer = setTimeout(() => {
        setIsHighlighted(false);
      }, 1500); // Slightly longer highlight for better visibility
      
      // Update the previous value reference
      previousValue.current = displayValue;
      
      return () => clearTimeout(timer);
    }
  }, [displayValue, signal.name, source]);
  
  // Get CSS class based on update source
  const getSourceClass = () => {
    if (!updateSource) return '';
    
    switch (updateSource) {
      case 'verification':
        return 'source-verification';
      case 'verification_mismatch':
        return 'source-mismatch';
      case 'write_request':
        return 'source-write';
      case 'realtime':
        return 'source-realtime';
      default:
        return '';
    }
  };
  
  return (
    <tr
      id={`signal-${signal.name}`}
      data-signal-id={signal.name}
      className={`${isHighlighted ? 'row-highlight' : ''} ${getSourceClass()}`}
    >
      <td>{signal.signal_name || 'N/A'}</td>
      <td><small>{signal.signal_type || 'N/A'}</small></td>
      <td className={`signal-value-cell ${isHighlighted ? 'highlight' : ''}`}>
        <ValueDisplay value={displayValue} signalType={signal.signal_type} />
        {updateSource && (
          <span className="update-source" title={`Last update source: ${updateSource}`}>
            <small>{updateSource === 'verification' ? '✓' :
                   updateSource === 'verification_mismatch' ? '!' :
                   updateSource === 'write_request' ? '↑' :
                   updateSource === 'realtime' ? '↓' : '•'}</small>
          </span>
        )}
      </td>
      <td>
        <code>{signal.modbus_address !== undefined ? signal.modbus_address : 'N/A'}</code>
      </td>
      <td className="signal-actions">
        <ActionButtons signal={{...signal, value: displayValue}} />
      </td>
    </tr>
  );
};

export default SignalRow;