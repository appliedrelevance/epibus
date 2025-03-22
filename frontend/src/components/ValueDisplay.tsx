import React from 'react';
import './ValueDisplay.css';

interface ValueDisplayProps {
  value: boolean | number | string | null | undefined;
  signalType: string;
}

const ValueDisplay: React.FC<ValueDisplayProps> = ({ value, signalType: _signalType }) => {
  if (value === undefined || value === null) {
    return <span className="text-muted">N/A</span>;
  }
  
  // For boolean values (Digital signals)
  if (typeof value === 'boolean') {
    return value ? (
      <span className="signal-indicator green">ON</span>
    ) : (
      <span className="signal-indicator red">OFF</span>
    );
  }
  
  // For numeric values (Analog signals)
  if (typeof value === 'number') {
    // Format the number with 2 decimal places
    return <span>{value.toFixed(2)}</span>;
  }
  
  // For string values or any other type
  return <span>{String(value)}</span>;
};

export default ValueDisplay;