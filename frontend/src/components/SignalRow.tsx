import React, { useState, useEffect } from 'react';
import { ModbusSignal } from '../App';
import ValueDisplay from './ValueDisplay';
import ActionButtons from './ActionButtons';
import './SignalRow.css';

interface SignalRowProps {
  signal: ModbusSignal;
}

const SignalRow: React.FC<SignalRowProps> = ({ signal }) => {
  const [isHighlighted, setIsHighlighted] = useState<boolean>(false);
  
  // Highlight the row when the value changes
  useEffect(() => {
    setIsHighlighted(true);
    
    const timer = setTimeout(() => {
      setIsHighlighted(false);
    }, 1000);
    
    return () => clearTimeout(timer);
  }, [signal.value]);
  
  return (
    <tr id={`signal-${signal.name}`} data-signal-id={signal.name}>
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