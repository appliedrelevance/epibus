import React from 'react';
import { Slider } from '@/components/ui/slider';
import { Activity } from 'lucide-react';

interface AnalogSignalProps {
    value: number;
    onChange?: (value: number) => void;
}

export const AnalogSignal: React.FC<AnalogSignalProps> = ({ value, onChange }) => (
    <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
            <Activity className="h-4 w-4" />
            <span className="text-sm font-medium">{value.toFixed(2)}</span>
        </div>
        <Slider
            value={[value]}
            min={0}
            max={100}
            step={0.1}
            onValueChange={v => onChange?.(v[0])}
        />
    </div>
);

export default AnalogSignal;