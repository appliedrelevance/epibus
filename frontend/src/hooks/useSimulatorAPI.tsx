// src/hooks/useSimulatorAPI.tsx
import { useFrappeGetCall, useFrappePostCall, FrappeError } from 'frappe-react-sdk';
import type { ModbusSimulator, SimulatorResponse } from '../types/simulator';

export function useSimulatorAPI() {
    // Use our custom API endpoint to get simulators with signals
    const { data, error: simulatorsError, mutate: refetchSimulators } =
        useFrappeGetCall<{
            message: ModbusSimulator[]
        }>(
            'epibus.epibus.api.simulator.list_simulators'
        );

    // Log the response for debugging
    console.log('🔍 API Response:', data);

    // Use dedicated hooks for start/stop operations
    const { call: startSimulatorCall } =
        useFrappePostCall<SimulatorResponse>('epibus.epibus.api.simulator.start_simulator');

    const { call: stopSimulatorCall } =
        useFrappePostCall<SimulatorResponse>('epibus.epibus.api.simulator.stop_simulator');

    // Extract simulators from response
    const simulators = (data?.message || []) as ModbusSimulator[];

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