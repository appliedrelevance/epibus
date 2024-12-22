// src/App.tsx
import React from 'react'  // Make sure React is imported first
import { FrappeProvider } from './components/providers/FrappeProvider'
import { PLCSimulator } from './components/PLCSimulator'

export default function App() {
  return (
    <FrappeProvider>
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <h1 className="text-2xl font-bold mb-4">PLC Simulator</h1>
          <PLCSimulator />
        </div>
      </div>
    </FrappeProvider>
  )
}