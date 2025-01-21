import { FrappeProvider } from 'frappe-react-sdk';
import { PLCSimulator } from './components/PLCSimulator';
import { UserProvider } from './contexts/UserContext';
import ProtectedRoute from './components/ProtectedRoute';
import { useEffect, useState } from 'react';

export default function App() {
  const [csrfToken, setCsrfToken] = useState<string | null>(null);

  useEffect(() => {
    // Fetch CSRF token when app loads
    fetch('/api/method/epibus.epibus.api.simulator.get_csrf_token')
      .then(r => r.json())
      .then(data => {
        console.log('🔑 Got CSRF token');
        if (data.message?.csrf_token) { // One less .message nesting
          setCsrfToken(data.message.csrf_token);
        }
      })
      .catch(err => {
        console.error('❌ Error getting CSRF token:', err);
      });
  }, []);

  const frappeConfig = {
    url: 'http://localhost:8000',
    socketPort: '9000',
    customHeaders: csrfToken ? {
      'X-Frappe-CSRF-Token': csrfToken
    } : undefined
  };

  if (!csrfToken) {
    return <div className="flex justify-center p-8">Loading...</div>;
  }

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