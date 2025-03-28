import React, { useState } from 'react';
import { useSignalMonitorContext } from '../contexts/SignalMonitorContext';

interface SignalControlProps {
  signalName: string;
  label?: string;
  className?: string;
}

export const SignalControl: React.FC<SignalControlProps> = ({
  signalName,
  label,
  className = ''
}) => {
  const { signals, writeSignal } = useSignalMonitorContext();
  const [isWriting, setIsWriting] = useState(false);
  
  // Get signal value
  const signal = signals[signalName];
  const value = signal?.value;
  const isDigital = typeof value === 'boolean';
  
  // Check if signal exists
  if (signal === undefined) {
    return (
      <div className={`signal-control ${className}`}>
        <div className="p-4 bg-gray-100 rounded-lg">
          <p className="text-gray-500">Signal not found: {signalName}</p>
        </div>
      </div>
    );
  }
  
  // Handle digital signal toggle
  const handleToggle = async (checked: boolean) => {
    setIsWriting(true);
    try {
      await writeSignal(signalName, checked);
    } catch (error) {
      console.error('Error toggling signal:', error);
    } finally {
      setIsWriting(false);
    }
  };
  
  // Handle analog signal change
  const handleSliderChange = async (value: number) => {
    setIsWriting(true);
    try {
      await writeSignal(signalName, value);
    } catch (error) {
      console.error('Error updating signal:', error);
    } finally {
      setIsWriting(false);
    }
  };
  
  return (
    <div className={`signal-control ${className}`}>
      <div className="p-4 bg-white rounded-lg shadow">
        <div className="flex justify-between items-center">
          <span className="font-medium">{label || signalName}</span>
          
          {isDigital ? (
            <div className="relative inline-block w-10 h-5 transition duration-200 ease-in-out rounded-full cursor-pointer">
              <input
                type="checkbox"
                className="absolute w-0 h-0 opacity-0"
                checked={!!value}
                onChange={(e) => handleToggle(e.target.checked)}
                disabled={isWriting}
              />
              <span
                className={`block w-10 h-5 rounded-full ${value ? 'bg-blue-600' : 'bg-gray-300'}`}
              />
              <span
                className={`absolute block w-4 h-4 mt-0.5 ml-0.5 rounded-full transition-transform duration-200 ease-in-out bg-white ${
                  value ? 'transform translate-x-5' : ''
                }`}
              />
            </div>
          ) : (
            <div className="w-full flex flex-col pl-4">
              <input
                type="range"
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                min="0"
                max="100"
                value={Number(value) || 0}
                onChange={(e) => handleSliderChange(parseInt(e.target.value))}
                disabled={isWriting}
              />
              <span className="text-sm text-right mt-1">{value}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
