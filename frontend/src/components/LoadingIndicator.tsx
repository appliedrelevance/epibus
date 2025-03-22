import React from 'react';
import './LoadingIndicator.css';

const LoadingIndicator: React.FC = () => {
  return (
    <div id="loading" className="text-center mb-4">
      <div className="spinner-border text-primary" role="status">
        <span className="sr-only">Loading...</span>
      </div>
    </div>
  );
};

export default LoadingIndicator;