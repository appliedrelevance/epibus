// hooks/useSimulator.ts
import { useState, useEffect, useCallback } from 'react'

export interface IOPoint {
  name: string
  address: number
  type: 'input' | 'output' | 'register'
  value: number | boolean
  plc_address?: string
}

interface SimulatorState {
  isConnected: boolean
  ioPoints: IOPoint[]
  error: string | null
}

interface UseSimulatorReturn extends SimulatorState {
  connect: () => Promise<void>
  disconnect: () => Promise<void>
  togglePoint: (address: number, type: string) => Promise<void>
  setValue: (address: number, type: string, value: number | boolean) => Promise<void>
}

export function useSimulator(): UseSimulatorReturn {
  const [state, setState] = useState<SimulatorState>({
    isConnected: false,
    ioPoints: [],
    error: null
  })

  const fetchIOPoints = useCallback(async () => {
    try {
      const response = await fetch('/api/method/epibus.simulator.get_io_points')
      const data = await response.json()
      if (data.message) {
        setState(prev => ({ ...prev, ioPoints: data.message }))
      }
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        error: 'Failed to fetch I/O points'
      }))
    }
  }, [])

  const connect = useCallback(async () => {
    try {
      const response = await fetch('/api/method/epibus.simulator.start_simulator', {
        method: 'POST'
      })
      const data = await response.json()
      if (data.message) {
        setState(prev => ({ ...prev, isConnected: true, error: null }))
        await fetchIOPoints()
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        isConnected: false,
        error: 'Failed to connect to simulator'
      }))
    }
  }, [fetchIOPoints])

  const disconnect = useCallback(async () => {
    try {
      const response = await fetch('/api/method/epibus.simulator.stop_simulator', {
        method: 'POST'
      })
      const data = await response.json()
      if (data.message) {
        setState(prev => ({ 
          ...prev, 
          isConnected: false, 
          error: null,
          ioPoints: prev.ioPoints.map(point => ({ ...point, value: false }))
        }))
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: 'Failed to disconnect from simulator'
      }))
    }
  }, [])

  const togglePoint = useCallback(async (address: number, type: string) => {
    try {
      const point = state.ioPoints.find(p => p.address === address && p.type === type)
      if (!point) return

      const endpoint = type === 'output' ? 'set_output' : 'set_input'
      const response = await fetch(`/api/method/epibus.simulator.${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          address,
          value: !point.value
        })
      })
      const data = await response.json()
      if (data.message) {
        await fetchIOPoints()
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: `Failed to toggle ${type} at address ${address}`
      }))
    }
  }, [state.ioPoints, fetchIOPoints])

  const setValue = useCallback(async (address: number, type: string, value: number | boolean) => {
    try {
      const endpoint = type === 'register' ? 'set_register' : 'set_output'
      const response = await fetch(`/api/method/epibus.simulator.${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ address, value })
      })
      const data = await response.json()
      if (data.message) {
        await fetchIOPoints()
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: `Failed to set value for ${type} at address ${address}`
      }))
    }
  }, [fetchIOPoints])

  useEffect(() => {
    if (state.isConnected) {
      // Set up WebSocket connection for real-time updates
      const socket = new WebSocket('ws://localhost:8000/socket.io')
      
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'io_update') {
          fetchIOPoints()
        }
      }

      socket.onerror = () => {
        setState(prev => ({
          ...prev,
          error: 'WebSocket connection failed'
        }))
      }

      return () => {
        socket.close()
      }
    }
  }, [state.isConnected, fetchIOPoints])

  return {
    ...state,
    connect,
    disconnect,
    togglePoint,
    setValue
  }
}