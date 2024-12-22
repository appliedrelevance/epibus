declare global {
    interface Window {
      frappe: {
        call: (opts: { 
          method: string;
          args?: Record<string, any>;
        }) => Promise<{
          exc: boolean;
          message?: {
            success?: boolean;
            error?: string;
            running?: boolean;
            port?: number;
            status?: string;
            [key: string]: any;
          };
        }>;
        set_route: (...args: string[]) => void;
        realtime: {
          on: (event: string, callback: () => void) => void;
          off: (event: string, callback: () => void) => void;
        };
      };
    }
  }
  
  export {}