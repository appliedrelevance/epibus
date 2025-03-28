// Configuration for the PLC Bridge SSE server

// Get the current hostname
const hostname = window.location.hostname;

// Define the SSE server URL
// If we're on localhost, use localhost:7654
// Otherwise, use the current hostname with port 7654
export const SSE_SERVER_URL = hostname === 'localhost'
  ? 'http://localhost:7654'
  : `http://${hostname}:7654`;

// Define a flag to enable/disable SSE connection attempts
// This can be set to false when the PLC Bridge is known to be unavailable
// to prevent excessive connection attempts
export const ENABLE_SSE_CONNECTION = true; // Re-enabled to use the real PLC Bridge

// Define a mock endpoint for testing when the PLC Bridge is unavailable
// This will be used when ENABLE_SSE_CONNECTION is false
export const MOCK_SERVER_URL = '/api/mock-plc-bridge';

// Export other configuration values as needed
// Use the real or mock endpoints based on the ENABLE_SSE_CONNECTION flag
export const SSE_EVENTS_ENDPOINT = ENABLE_SSE_CONNECTION
  ? `${SSE_SERVER_URL}/events`
  : `${MOCK_SERVER_URL}/events`;
  
export const SSE_SIGNALS_ENDPOINT = ENABLE_SSE_CONNECTION
  ? `${SSE_SERVER_URL}/signals`
  : `${MOCK_SERVER_URL}/signals`;
  
export const SSE_WRITE_SIGNAL_ENDPOINT = ENABLE_SSE_CONNECTION
  ? `${SSE_SERVER_URL}/write_signal`
  : `${MOCK_SERVER_URL}/write_signal`;
  
export const SSE_EVENTS_HISTORY_ENDPOINT = ENABLE_SSE_CONNECTION
  ? `${SSE_SERVER_URL}/events/history`
  : `${MOCK_SERVER_URL}/events/history`;