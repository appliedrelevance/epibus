import React from 'react';
import { Toggle } from '@/components/ui/toggle';
import { CircleDot, Circle } from 'lucide-react';

interface DigitalSignalProps {
    value: boolean;
    onChange?: (value: boolean) => void;
}

export const DigitalSignal: React.FC<DigitalSignalProps> = ({ value, onChange }) => (
    <Toggle
        pressed={value}
        onPressedChange={onChange}
        className="w-full justify-start gap-2"
    >
        {value ? (
            <CircleDot className="h-4 w-4 text-green-500" />
        ) : (
            <Circle className="h-4 w-4 text-gray-400" />
        )}
        {value ? 'ON' : 'OFF'}
    </Toggle>
);

export default DigitalSignal;