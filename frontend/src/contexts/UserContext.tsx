// UserContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useFrappeGetCall } from 'frappe-react-sdk';

interface User {
  full_name: string;
  email: string;
  // Add other user properties as needed
}

interface UserContextProps {
  user: User | null;
  isLoading: boolean;
  hasError: boolean;
}

const UserContext = createContext<UserContextProps | undefined>(undefined);

export const UserProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const { data, error } = useFrappeGetCall<{ message: User }>('frappe.auth.get_logged_user');

  useEffect(() => {
    if (data?.message) {
      setUser(data.message);
      setHasError(false);
    } else if (error) {
      console.error('🔴 Error fetching session:', error);
      setUser(null);
      setHasError(true);
    }
    setIsLoading(false);
  }, [data, error]);

  return (
    <UserContext.Provider value={{ user, isLoading, hasError }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) throw new Error('useUser must be used within a UserProvider');
  return context;
};

