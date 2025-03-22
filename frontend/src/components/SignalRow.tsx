import React, { useState, useEffect, useRef } from 'react';
import { ModbusSignal } from '../App';
import ValueDisplay from './ValueDisplay';
import ActionButtons from './ActionButtons';
import './SignalRow.css';

interface SignalRowProps {
  signal: ModbusSignal;
}

const SignalRow: React.FC<SignalRowProps> = ({ signal }) => {
  const [isHighlighted, setIsHighlighted] = useState<boolean>(false);
  const previousValue = useRef<any>(signal.value);
  
  // Highlight the row when the value changes
  useEffect(() => {
    // Only highlight if the value has actually changed
    if (previousValue.current !== signal.value) {
      console.log(`Signal ${signal.name} value changed: ${previousValue.current} -> ${signal.value}`);
      setIsHighlighted(true);
      
      const timer = setTimeout(() => {
        setIsHighlighted(false);
      }, 1500); // Slightly longer highlight for better visibility
      
      // Update the previous value reference
      previousValue.current = signal.value;
      
      return () => clearTimeout(timer);
    }
  }, [signal.value, signal.name]);
  
  return (
    <tr
      id={`signal-${signal.name}`}
      data-signal-id={signal.name}
      className={isHighlighted ? 'row-highlight' : ''}
    >
      <td>{signal.signal_name || 'N/A'}</td>
      <td><small>{signal.signal_type || 'N/A'}</small></td>
      <td className={`signal-value-cell ${isHighlighted ? 'highlight' : ''}`}>
        <ValueDisplay value={signal.value} signalType={signal.signal_type} />
      </td>
      <td>
        <code>{signal.modbus_address !== undefined ? signal.modbus_address : 'N/A'}</code>
      </td>
      <td className="signal-actions">
        <ActionButtons signal={signal} />
      </td>
    </tr>
  );
};

export default SignalRow;