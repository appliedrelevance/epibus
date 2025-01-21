// src/types/simulator.ts

export type ServerStatus = 'Stopped' | 'Starting' | 'Running' | 'Stopping' | 'Error';
export type EquipmentType = 'PLC' | 'Robot' | 'Simulator' | 'Other';

export interface ModbusSignal {
  name: string;
  signal_name: string;
  signal_type: 'Digital Output Coil' | 'Digital Input Contact' | 'Analog Input Register' | 'Analog Output Register' | 'Holding Register';
  modbus_address: number;
  plc_address: string;
  digital_value?: boolean;
  float_value?: number;
  parent?: string;
  parentfield?: string;
  parenttype?: string;
  idx?: number;
}

export interface ModbusSimulator {
  name: string;
  simulator_name: string;
  equipment_type: EquipmentType;
  server_status: ServerStatus;
  server_port: number;
  enabled: boolean;
  last_status_update: string;
  error_message?: string;
  // Declare io_points as a child table field
  io_points: ModbusSignal[];
}

export interface SimulatorResponse {
  message?: {
    success: boolean;
    error?: string;
    running?: boolean;
    port?: number;
  };
  exc?: boolean;
}