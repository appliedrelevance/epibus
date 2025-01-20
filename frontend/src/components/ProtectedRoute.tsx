// ProtectedRoute.tsx
import React from 'react';
import { useUser } from '../contexts/UserContext';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isLoading, hasError } = useUser();

  if (isLoading) {
    return <div className="flex justify-center p-8">Loading...</div>;
  }

  if (hasError) {
    return <div className="text-red-500 p-8">Error: Unable to fetch session</div>;
  }

  return <>{children}</>;
};

export default ProtectedRoute;