import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { DigitalSignal } from '@/components/signals';
import { AnalogSignal } from '@/components/signals';
import type { ModbusSignal } from '@/types/simulator';

interface SignalCardProps {
    signal: ModbusSignal;
    onValueChange?: (value: number | boolean) => void;
}

export const SignalCard: React.FC<SignalCardProps> = ({ signal, onValueChange }) => {
    const isDigital = signal.signal_type.includes('Digital');

    return (
        <Card className="w-48">
            <CardContent className="p-4">
                <div className="flex flex-col gap-2">
                    <div className="text-sm font-medium truncate" title={signal.signal_name}>
                        {signal.signal_name}
                    </div>
                    <div className="text-xs text-muted-foreground">
                        {signal.plc_address}
                    </div>
                    {isDigital ? (
                        <DigitalSignal
                            value={signal.digital_value || false}
                            onChange={onValueChange as (value: boolean) => void}
                        />
                    ) : (
                        <AnalogSignal
                            value={signal.float_value || 0}
                            onChange={onValueChange as (value: number) => void}
                        />
                    )}
                </div>
            </CardContent>
        </Card>
    );
};

export default SignalCard;