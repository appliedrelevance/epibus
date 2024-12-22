import React from 'react';
import { useUser } from '../contexts/UserContext';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { user, isLoading, hasError } = useUser();
  
    if (isLoading) return <div>Loading...</div>;

    if (hasError) {
        // Redirect to login or show an error
        return <div>Error: Unable to fetch session. Please try again.</div>;
      }

    // if (!user) {
    //   // Redirect to Frappe login page
    //   window.location.href = 'http://localhost:8000/login'; // Update this to match your Frappe server
    //   return null;
    // }
    

    return <>{children}</>;
  };
  

export default ProtectedRoute;
