import React, { createContext, useContext, useState, useEffect } from 'react';
import { useFrappeGetCall } from 'frappe-react-sdk';

interface UserContextProps {
  user: string | null;
  isLoading: boolean;
  hasError: boolean;
}

const UserContext = createContext<UserContextProps | undefined>(undefined);

// Use React.PropsWithChildren to include the children prop type
export const UserProvider: React.FC<React.PropsWithChildren<{}>> = ({ children }) => {
  const [user, setUser] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const { data, error } = useFrappeGetCall<{ message: string }>('frappe.auth.get_logged_user');

  useEffect(() => {
    const fetchSession = async () => {
      try {
        if (data && data.message) {
          setUser(data.message);
        } else if (error) {
          console.error('Error fetching session:', error);
          setUser(null);
        }
      } catch (err) {
        console.error('Unexpected error fetching session:', err);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSession();
  }, [data, error]);

  return (
    <UserContext.Provider value={{ user, isLoading }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) throw new Error('useUser must be used within a UserProvider');
  return context;
};
