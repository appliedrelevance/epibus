import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Wait for next tick to ensure React is initialized
setTimeout(() => {
  const root = ReactDOM.createRoot(document.getElementById('root')!)
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
}, 0)