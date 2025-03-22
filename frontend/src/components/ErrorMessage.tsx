import React, { useState, useEffect } from 'react';
import './ErrorMessage.css';

interface ErrorMessageProps {
  message: string;
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({ message }) => {
  const [visible, setVisible] = useState<boolean>(true);
  
  // Auto-hide after 5 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
    }, 5000);
    
    return () => clearTimeout(timer);
  }, [message]);
  
  if (!visible) return null;
  
  return (
    <div id="error-message" className="alert alert-danger mb-4">
      {message}
    </div>
  );
};

export default ErrorMessage;