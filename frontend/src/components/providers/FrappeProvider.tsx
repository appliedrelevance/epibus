// src/components/providers/FrappeProvider.tsx
import { FrappeProvider as Provider } from 'frappe-react-sdk';
import type { ReactNode } from 'react';

const frappeConfig = {
  url: 'http://localhost:8000',
  socketPort: '9000' 
};

interface FrappeProviderProps {
  children: ReactNode;
}

export function FrappeProvider({ children }: FrappeProviderProps) {
  return (
    <Provider {...frappeConfig}>
      {children}
    </Provider>
  );
}