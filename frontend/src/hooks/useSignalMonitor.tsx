// src/hooks/useSignalMonitor.tsx
import { useState, useEffect } from 'react';
import { useFrappePostCall } from 'frappe-react-sdk';
import type { SignalUpdate } from '@/types/simulator';

export function useSignalMonitor(signalName: string) {
    const [value, setValue] = useState<number | boolean | null>(null);
    const [lastUpdate, setLastUpdate] = useState<string>('');
    const [error, setError] = useState<Error | null>(null);

    const { call: startMonitoring } = useFrappePostCall('epibus.signal_monitor.start_monitoring');

    useEffect(() => {
        // Start monitoring the signal
        startMonitoring({ signal_name: signalName })
            .then(() => {
                console.log(`Started monitoring ${signalName}`);
            })
            .catch((err) => {
                console.error('Failed to start monitoring:', err);
                setError(err);
            });

        // Set up realtime listener
        const handleUpdate = (data: SignalUpdate) => {
            if (data.signal === signalName) {
                setValue(data.value);
                setLastUpdate(data.timestamp);
            }
        };

        // Use existing frappe realtime interface
        if (window.frappe) {
            window.frappe.realtime.on('modbus_signal_update', handleUpdate);
        }

        // Cleanup
        return () => {
            if (window.frappe) {
                window.frappe.realtime.off('modbus_signal_update', handleUpdate);
            }
        };
    }, [signalName, startMonitoring]);

    return {
        value,
        lastUpdate,
        error
    };
}