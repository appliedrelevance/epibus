import React, { useState, useEffect, useRef } from 'react';
import { ModbusSignal } from '../App';
import ValueDisplay from './ValueDisplay';
import ActionButtons from './ActionButtons';
import { useSignalMonitor } from '../hooks/useSignalMonitor';
import './SignalRow.css';

interface SignalRowProps {
  signal: ModbusSignal;
}

const SignalRow: React.FC<SignalRowProps> = ({ signal }) => {
  const [isHighlighted, setIsHighlighted] = useState<boolean>(false);
  const { signals: realtimeSignals } = useSignalMonitor();
  
  // Get the real-time value if available, otherwise use the prop value
  const realtimeValue = realtimeSignals[signal.name]?.value;
  const displayValue = realtimeValue !== undefined ? realtimeValue : signal.value;
  
  const previousValue = useRef<any>(displayValue);
  
  // Highlight the row when the value changes
  useEffect(() => {
    // Only highlight if the value has actually changed
    if (previousValue.current !== displayValue) {
      console.log(`Signal ${signal.name} value changed: ${previousValue.current} -> ${displayValue}`);
      setIsHighlighted(true);
      
      const timer = setTimeout(() => {
        setIsHighlighted(false);
      }, 1500); // Slightly longer highlight for better visibility
      
      // Update the previous value reference
      previousValue.current = displayValue;
      
      return () => clearTimeout(timer);
    }
  }, [displayValue, signal.name]);
  
  return (
    <tr
      id={`signal-${signal.name}`}
      data-signal-id={signal.name}
      className={isHighlighted ? 'row-highlight' : ''}
    >
      <td>{signal.signal_name || 'N/A'}</td>
      <td><small>{signal.signal_type || 'N/A'}</small></td>
      <td className={`signal-value-cell ${isHighlighted ? 'highlight' : ''}`}>
        <ValueDisplay value={displayValue} signalType={signal.signal_type} />
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