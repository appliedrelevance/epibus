import { useFrappeGetCall } from 'frappe-react-sdk';
import { useState, useEffect } from 'react';

export const useSession = () => {
  const [user, setUser] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const { data, error } = useFrappeGetCall<{ message: string }>('frappe.auth.get_logged_user');

  useEffect(() => {
    if (data) {
      setUser(data.message);
      setIsLoading(false);
    } else if (error) {
      console.error('Error fetching session:', error);
      setUser(null);
      setIsLoading(false);
      setHasError(true); // Prevent retries
    }
  }, [data, error]);

  return { user, isLoading, hasError };
};
