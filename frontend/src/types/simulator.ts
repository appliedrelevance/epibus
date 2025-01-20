// src/types/simulator.ts

export type ServerStatus = 'Stopped' | 'Starting' | 'Running' | 'Stopping' | 'Error';

export interface ModbusSignal {
  signal_name: string;
  signal_type: 'Digital Output Coil' | 'Digital Input Contact' | 'Analog Input Register' | 'Analog Output Register' | 'Holding Register';
  modbus_address: number;
  plc_address: string;
  digital_value?: boolean;
  float_value?: number;
}

export interface ModbusSimulator {
  name: string;
  simulator_name: string;
  equipment_type: 'PLC' | 'Robot' | 'Conveyor' | 'Sensor Array' | 'Machine Tool' | 'Custom' | null;
  server_status: ServerStatus;
  server_port: number;
  enabled: boolean;
  last_status_update: string;
  error_message?: string;
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