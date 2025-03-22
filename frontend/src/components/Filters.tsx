import React from 'react';
import './Filters.css';

interface FiltersProps {
  activeFilters: {
    deviceType: string;
    signalType: string;
  };
  onFilterChange: (filterType: 'deviceType' | 'signalType', value: string) => void;
}

const Filters: React.FC<FiltersProps> = ({ activeFilters, onFilterChange }) => {
  return (
    <div className="row mb-4">
      <div className="col-md-4">
        <select 
          className="form-control" 
          id="device-type-filter"
          value={activeFilters.deviceType}
          onChange={(e) => onFilterChange('deviceType', e.target.value)}
        >
          <option value="">All Device Types</option>
          <option value="PLC">PLC</option>
          <option value="Robot">Robot</option>
          <option value="Simulator">Simulator</option>
          <option value="Other">Other</option>
        </select>
      </div>
      <div className="col-md-4">
        <select 
          className="form-control" 
          id="signal-type-filter"
          value={activeFilters.signalType}
          onChange={(e) => onFilterChange('signalType', e.target.value)}
        >
          <option value="">All Signal Types</option>
          <option value="Digital Output Coil">Digital Output Coil</option>
          <option value="Digital Input Contact">Digital Input Contact</option>
          <option value="Analog Input Register">Analog Input Register</option>
          <option value="Analog Output Register">Analog Output Register</option>
          <option value="Holding Register">Holding Register</option>
        </select>
      </div>
    </div>
  );
};

export default Filters;