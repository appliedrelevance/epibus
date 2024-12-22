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
  connect: () => void
  disconnect: () => void
  togglePoint: (address: number, type: string) => void
  setValue: (address: number, type: string, value: number | boolean) => void
}

export function useSimulator(simulatorName: string): UseSimulatorReturn {
  const [state, setState] = useState<SimulatorState>({
    isConnected: false,
    ioPoints: [],
    error: null
  })

  const fetchIOPoints = useCallback(() => {
    if (!(window as Window).frappe) return

    ;(window as Window).frappe.call({
      method: 'epibus.epibus.simulator.simulator.get_io_points',
      args: { simulator_name: simulatorName }
    }).then(r => {
      if (!r.exc && Array.isArray(r.message)) {
        const points: IOPoint[] = r.message.map(point => ({
          name: String(point.name),
          address: Number(point.address),
          type: point.type as 'input' | 'output' | 'register',
          value: point.value,
          plc_address: point.plc_address
        }))
        setState(prev => ({ ...prev, ioPoints: points }))
      } else {
        setState(prev => ({ 
          ...prev, 
          error: 'Failed to fetch I/O points'
        }))
      }
    })
  }, [simulatorName])

  const connect = useCallback(() => {
    if (!(window as Window).frappe) return

    ;(window as Window).frappe.call({
      method: 'epibus.epibus.simulator.simulator.start_simulator',
      args: { simulator_name: simulatorName }
    }).then(r => {
      if (!r.exc && r.message?.success) {
        setState(prev => ({ ...prev, isConnected: true, error: null }))
        fetchIOPoints()
      } else {
        setState(prev => ({
          ...prev,
          isConnected: false,
          error: r.message?.error || 'Failed to connect to simulator'
        }))
      }
    })
  }, [simulatorName, fetchIOPoints])

  const disconnect = useCallback(() => {
    if (!(window as Window).frappe) return

    ;(window as Window).frappe.call({
      method: 'epibus.epibus.simulator.simulator.stop_simulator',
      args: { simulator_name: simulatorName }
    }).then(r => {
      if (!r.exc && r.message?.success) {
        setState(prev => ({ 
          ...prev, 
          isConnected: false, 
          error: null,
          ioPoints: prev.ioPoints.map(point => ({ ...point, value: false }))
        }))
      } else {
        setState(prev => ({
          ...prev,
          error: r.message?.error || 'Failed to disconnect from simulator'
        }))
      }
    })
  }, [simulatorName])

  const togglePoint = useCallback((address: number, type: string) => {
    if (!(window as Window).frappe) return

    const point = state.ioPoints.find(p => p.address === address && p.type === type)
    if (!point) return

    const method = type === 'output' 
      ? 'epibus.epibus.simulator.simulator.set_output'
      : 'epibus.epibus.simulator.simulator.set_input'

    ;(window as Window).frappe.call({
      method,
      args: {
        simulator_name: simulatorName,
        address,
        value: !point.value
      }
    }).then(r => {
      if (!r.exc && r.message?.success) {
        fetchIOPoints()
      } else {
        setState(prev => ({
          ...prev,
          error: r.message?.error || `Failed to toggle ${type} at address ${address}`
        }))
      }
    })
  }, [state.ioPoints, simulatorName, fetchIOPoints])

  const setValue = useCallback((address: number, type: string, value: number | boolean) => {
    if (!(window as Window).frappe) return

    const method = type === 'register' 
      ? 'epibus.epibus.simulator.simulator.set_register'
      : 'epibus.epibus.simulator.simulator.set_output'

    ;(window as Window).frappe.call({
      method,
      args: {
        simulator_name: simulatorName,
        address,
        value
      }
    }).then(r => {
      if (!r.exc && r.message?.success) {
        fetchIOPoints()
      } else {
        setState(prev => ({
          ...prev,
          error: r.message?.error || `Failed to set value for ${type} at address ${address}`
        }))
      }
    })
  }, [simulatorName, fetchIOPoints])

  useEffect(() => {
    // Only run if frappe is available
    if (!(window as Window).frappe) return

    // Check initial connection status
    ;(window as Window).frappe.call({
      method: 'epibus.epibus.simulator.simulator.get_server_status',
      args: { simulator_name: simulatorName }
    }).then(r => {
      if (!r.exc) {
        setState(prev => ({ 
          ...prev, 
          isConnected: r.message?.running || false
        }))
        if (r.message?.running) {
          fetchIOPoints()
        }
      }
    })

    // Set up realtime updates
    const handleUpdate = () => {
      fetchIOPoints()
    }

    ;(window as Window).frappe.realtime.on('simulator_value_update', handleUpdate)
    return () => {
      if ((window as Window).frappe) {
        ;(window as Window).frappe.realtime.off('simulator_value_update', handleUpdate)
      }
    }
  }, [simulatorName, fetchIOPoints])

  return {
    ...state,
    connect,
    disconnect,
    togglePoint,
    setValue
  }
}