import './styles/globals.css' // Update this path
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

setTimeout(() => {
  const root = ReactDOM.createRoot(document.getElementById('root')!)
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
}, 0)