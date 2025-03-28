// Configuration for the PLC Bridge SSE server

// Get the current hostname
const hostname = window.location.hostname;

// Define the SSE server URL
// If we're on localhost, use localhost:7654
// Otherwise, use the current hostname with port 7654
export const SSE_SERVER_URL = hostname === 'localhost' 
  ? 'http://localhost:7654'
  : `http://${hostname}:7654`;

// Export other configuration values as needed
export const SSE_EVENTS_ENDPOINT = `${SSE_SERVER_URL}/events`;
export const SSE_SIGNALS_ENDPOINT = `${SSE_SERVER_URL}/signals`;
export const SSE_WRITE_SIGNAL_ENDPOINT = `${SSE_SERVER_URL}/write_signal`;
export const SSE_EVENTS_HISTORY_ENDPOINT = `${SSE_SERVER_URL}/events/history`;