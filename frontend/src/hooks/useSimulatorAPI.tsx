// src/lib/api.ts
import { useFrappeGetCall, useFrappePostCall } from 'frappe-react-sdk';
import type { Simulator, SimulatorResponse } from '../types/simulator';

export function useSimulatorAPI() {
    const { data: rawSimulators, error: simulatorsError, mutate: refetchSimulators } =
        useFrappeGetCall<{ message: any[] }>('epibus.epibus.simulator.simulator.get_simulators');

    const { call: startSimulatorCall } =
        useFrappePostCall<SimulatorResponse>('epibus.epibus.simulator.simulator.start_simulator');

    const { call: stopSimulatorCall } =
        useFrappePostCall<SimulatorResponse>('epibus.epibus.simulator.simulator.stop_simulator');

    // Map raw simulator data to the expected format
    const simulators: Simulator[] = rawSimulators?.message.map((sim) => ({
        name: sim.name,
        connection_status: sim.status || 'Unknown', // Fallback if `status` is missing
        server_port: sim.port,
        enabled: true, // Assume enabled unless explicitly returned
        last_status_update: sim.last_status_update || new Date().toISOString(), // Mock value if not provided
    })) || [];

    const startSimulator = (simulatorName: string) => {
        return startSimulatorCall({ simulator_name: simulatorName })
            .then((response) => {
                refetchSimulators(); // Refresh simulator data after the action
                return response;
            })
            .catch((error) => {
                console.error('Error starting simulator:', error);
                throw error;
            });
    };

    const stopSimulator = (simulatorName: string) => {
        return stopSimulatorCall({ simulator_name: simulatorName })
            .then((response) => {
                refetchSimulators(); // Refresh simulator data after the action
                return response;
            })
            .catch((error) => {
                console.error('Error stopping simulator:', error);
                throw error;
            });
    };

    console.log('Processed Simulators:', simulators);
    console.log('Simulators Error:', simulatorsError);

    return {
        simulators,
        simulatorsError,
        startSimulator,
        stopSimulator,
        refetchSimulators,
    };
}
