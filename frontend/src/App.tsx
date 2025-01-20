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
          <main className="min-h-screen bg-background">
            <div className="container mx-auto p-8">
              <PLCSimulator />
            </div>
          </main>
        </ProtectedRoute>
      </UserProvider>
    </FrappeProvider>
  );
}