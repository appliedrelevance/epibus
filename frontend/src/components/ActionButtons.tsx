import React, { useState, useEffect } from 'react';
import { ModbusSignal } from '../App';
import { fetchWrapper } from '../utils/fetchWrapper';
import './ActionButtons.css';

interface ActionButtonsProps {
  signal: ModbusSignal;
}

// Create a custom event for local state updates
export const createSignalUpdateEvent = (signalId: string, value: any) => {
  const event = new CustomEvent('local-signal-update', {
    detail: { signal: signalId, value }
  });
  window.dispatchEvent(event);
  console.log('Dispatched local update event:', { signal: signalId, value });
};

const ActionButtons: React.FC<ActionButtonsProps> = ({ signal }) => {
  const [inputValue, setInputValue] = useState<number>(
    typeof signal.value === 'number' ? signal.value : 0
  );
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  
  // Update input value when signal value changes
  useEffect(() => {
    if (typeof signal.value === 'number') {
      setInputValue(signal.value);
    }
  }, [signal.value]);
  
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
    if (isUpdating) return;
    
    try {
      setIsUpdating(true);
      const newValue = !(signal.value as boolean);
      
      // Optimistically update UI immediately
      createSignalUpdateEvent(signal.name, newValue);
      
      const response = await fetchWrapper('/api/method/epibus.api.plc.update_signal', {
        method: 'POST',
        body: JSON.stringify({
          signal_id: signal.name,
          value: newValue
        })
      });
      
      // Only update if we got a valid response with a different value
      if (response && response.message && 
          response.message.value !== undefined && 
          response.message.value !== newValue) {
        createSignalUpdateEvent(signal.name, response.message.value);
      }
      
      // If we don't get a valid response value, assume our update was successful
      // and keep the optimistically updated value
      
      console.log('Toggle response:', response);
    } catch (error) {
      console.error('Error toggling signal:', error);
      alert(`Error toggling signal: ${error instanceof Error ? error.message : String(error)}`);
      
      // Revert to original value on error
      createSignalUpdateEvent(signal.name, signal.value);
    } finally {
      setIsUpdating(false);
    }
  };
  
  // Handle set value action for analog outputs and holding registers
  const handleSetValue = async () => {
    if (isUpdating) return;
    
    try {
      setIsUpdating(true);
      
      // Optimistically update UI immediately
      createSignalUpdateEvent(signal.name, inputValue);
      
      const response = await fetchWrapper('/api/method/epibus.api.plc.update_signal', {
        method: 'POST',
        body: JSON.stringify({
          signal_id: signal.name,
          value: inputValue
        })
      });
      
      // Only update if we got a valid response with a different value
      if (response && response.message && 
          response.message.value !== undefined && 
          response.message.value !== inputValue) {
        createSignalUpdateEvent(signal.name, response.message.value);
        setInputValue(response.message.value);
      }
      
      console.log('Set value response:', response);
    } catch (error) {
      console.error('Error setting signal value:', error);
      alert(`Error setting signal value: ${error instanceof Error ? error.message : String(error)}`);
      
      // Revert to original value on error
      createSignalUpdateEvent(signal.name, signal.value);
    } finally {
      setIsUpdating(false);
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
        className={`btn btn-sm btn-outline-primary toggle-signal ${isUpdating ? 'disabled' : ''}`}
        onClick={handleToggle}
        disabled={isUpdating}
      >
        {isUpdating ? 'Updating...' : 'Toggle'}
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
        disabled={isUpdating}
      />
      <div className="input-group-append">
        <button
          className={`btn btn-sm btn-outline-primary set-signal-value ${isUpdating ? 'disabled' : ''}`}
          onClick={handleSetValue}
          disabled={isUpdating}
        >
          {isUpdating ? 'Setting...' : 'Set'}
        </button>
      </div>
    </div>
  );
};

export default ActionButtons;