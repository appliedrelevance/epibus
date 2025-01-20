import { FrappeProvider } from 'frappe-react-sdk';
import { PLCSimulator } from './components/PLCSimulator';
import { UserProvider } from './contexts/UserContext';
import ProtectedRoute from './components/ProtectedRoute';

const frappeConfig = {
  url: 'http://localhost:8000',
  socketPort: '9000'
};

export default function App() {
  return (
    <FrappeProvider {...frappeConfig}>
      <UserProvider>
        <ProtectedRoute>
          <div className="min-h-screen bg-background">
            <div className="container py-8">
              <h1 className="text-2xl font-bold mb-4">PLC Simulator</h1>
              <PLCSimulator />
            </div>
          </div>
        </ProtectedRoute>
      </UserProvider>
    </FrappeProvider>
  );
}
