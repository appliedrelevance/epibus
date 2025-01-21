// src/hooks/useSimulatorAPI.tsx
import { useFrappeGetDocList, useFrappePostCall, FrappeError } from 'frappe-react-sdk';
import type { ModbusSimulator, SimulatorResponse } from '../types/simulator';

export function useSimulatorAPI() {


    // Use standard hook for getting simulator list with error handling
    const { data: rawSimulators, error: simulatorsError, mutate: refetchSimulators } =
        useFrappeGetDocList<ModbusSimulator>(
            'Modbus Simulator',
            {
                fields: ['*'],
                orderBy: {
                    field: 'modified',
                    order: 'desc'
                }
            }
        );

    // Use dedicated hooks for start/stop operations
    const { call: startSimulatorCall } =
        useFrappePostCall<SimulatorResponse>('epibus.epibus.api.simulator.start_simulator');

    const { call: stopSimulatorCall } =
        useFrappePostCall<SimulatorResponse>('epibus.epibus.api.simulator.stop_simulator');

    // No mapping needed - just pass through the data
    const simulators = rawSimulators || [];

    console.log('📊 Raw simulator data:', simulators);

    const startSimulator = (simulatorName: string) => {
        console.log('🚀 Starting simulator:', simulatorName);

        return startSimulatorCall({
            simulator_name: simulatorName
        })
            .then((response) => {
                console.log('✅ Start response:', response);
                if (response?.message?.error) {
                    throw new Error(response.message.error);
                }
                refetchSimulators();
                return response;
            })
            .catch((error: FrappeError) => {
                console.error('❌ Start error:', error);
                if (error.httpStatus === 400 && error.message?.includes('CSRF')) {
                    console.error('🔐 CSRF Token error - trying to refresh');
                    window.location.reload();
                    return;
                }
                throw error;
            });
    };

    const stopSimulator = (simulatorName: string) => {
        console.log('🛑 Stopping simulator:', simulatorName);

        return stopSimulatorCall({
            simulator_name: simulatorName
        })
            .then((response) => {
                console.log('✅ Stop response:', response);
                if (response?.message?.error) {
                    throw new Error(response.message.error);
                }
                refetchSimulators();
                return response;
            })
            .catch((error: FrappeError) => {
                console.error('❌ Stop error:', error);
                if (error.httpStatus === 403) {
                    console.error('🔐 CSRF Token error - trying to refresh');
                    window.location.reload();
                    return;
                }
                throw error;
            });
    };

    return {
        simulators,
        simulatorsError,
        startSimulator,
        stopSimulator,
        refetchSimulators,
    };
}