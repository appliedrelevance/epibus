import React from 'react';
import { SignalCard } from './signal-card';
import type { ModbusSignal } from '@/types/simulator';

interface SignalGridProps {
    signals: ModbusSignal[];
    onSignalChange?: (signalName: string, value: number | boolean) => void;
}

export const SignalGrid: React.FC<SignalGridProps> = ({ signals = [], onSignalChange }) => (
    <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.isArray(signals) && signals.map((signal) => (
            <SignalCard
                key={signal.signal_name}
                signal={signal}
                onValueChange={
                    onSignalChange
                        ? (value) => onSignalChange(signal.signal_name, value)
                        : undefined
                }
            />
        ))}
    </div>
);

export default SignalGrid;