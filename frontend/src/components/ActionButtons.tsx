import React, { useState } from 'react';
import { ModbusSignal } from '../App';
import { fetchWrapper } from '../utils/fetchWrapper';
import './ActionButtons.css';

interface ActionButtonsProps {
  signal: ModbusSignal;
}

const ActionButtons: React.FC<ActionButtonsProps> = ({ signal }) => {
  const [inputValue, setInputValue] = useState<number>(
    typeof signal.value === 'number' ? signal.value : 0
  );
  
  // Check if a signal type is writable
  const isSignalWritable = (signalType: string): boolean => {
    return (
      signalType === "Digital Output Coil" ||
      signalType === "Analog Output Register" ||
      signalType === "Holding Register"
    );
  };
  
  // Handle toggle action for digital outputs
  const handleToggle = async () => {
    try {
      await fetchWrapper('/api/method/epibus.www.warehouse_dashboard.set_signal_value', {
        method: 'POST',
        body: JSON.stringify({
          signal_id: signal.name,
          value: !(signal.value as boolean)
        })
      });
      
      // The actual value update will come through the real-time updates
    } catch (error) {
      console.error('Error toggling signal:', error);
      alert(`Error toggling signal: ${error instanceof Error ? error.message : String(error)}`);
    }
  };
  
  // Handle set value action for analog outputs and holding registers
  const handleSetValue = async () => {
    try {
      await fetchWrapper('/api/method/epibus.www.warehouse_dashboard.set_signal_value', {
        method: 'POST',
        body: JSON.stringify({
          signal_id: signal.name,
          value: inputValue
        })
      });
      
      // The actual value update will come through the real-time updates
    } catch (error) {
      console.error('Error setting signal value:', error);
      alert(`Error setting signal value: ${error instanceof Error ? error.message : String(error)}`);
    }
  };
  
  // If signal is not writable, return empty fragment
  if (!isSignalWritable(signal.signal_type)) {
    return <></>;
  }
  
  // For digital outputs, show toggle button
  if (signal.signal_type === "Digital Output Coil") {
    return (
      <button 
        className="btn btn-sm btn-outline-primary toggle-signal" 
        onClick={handleToggle}
      >
        Toggle
      </button>
    );
  }
  
  // For analog outputs and holding registers, show input field and set button
  return (
    <div className="input-group input-group-sm">
      <input 
        type="number" 
        className="form-control form-control-sm signal-value-input"
        value={inputValue}
        onChange={(e) => setInputValue(parseFloat(e.target.value))}
      />
      <div className="input-group-append">
        <button 
          className="btn btn-sm btn-outline-primary set-signal-value"
          onClick={handleSetValue}
        >
          Set
        </button>
      </div>
    </div>
  );
};

export default ActionButtons;