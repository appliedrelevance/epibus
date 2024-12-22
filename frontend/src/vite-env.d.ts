/// <reference types="vite/client" />

interface FrappeCall {
    method: string
    args?: Record<string, any>
    freeze?: boolean
    freeze_message?: string
  }
  
  interface FrappeResponse {
    exc: boolean
    message?: any
  }
  
  interface FrappeRealtime {
    on: (event: string, callback: () => void) => void
    off: (event: string, callback: () => void) => void
  }
  
  interface Frappe {
    call: (opts: FrappeCall) => Promise<FrappeResponse>
    realtime: FrappeRealtime
  }
  
  declare global {
    const frappe: Frappe
    interface Window {
      frappe: Frappe
    }
  }