// src/types/simulator.ts

export interface Simulator {
    name: string;
    simulator_name: string;
    equipment_type?: string;
    connection_status: 'Connected' | 'Disconnected' | 'Error' | 'Connecting';
    server_port: number;
    enabled: boolean;
    last_status_update: string;
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
  
  export interface IOPoint {
    name: string;
    location_name: string;
    signal_type: string;
    modbus_address: number;
    plc_address: string;
    value: string | number | boolean;
  }