// Simple React component to monitor PLC signals
const { useState, useEffect, useRef } = React;

function App() {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const [socketStatus, setSocketStatus] = useState('Initializing...');

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Clear messages
  const clearMessages = () => {
    setMessages([]);
  };

  // Setup socket connection and event listeners
  useEffect(() => {
    let checkInterval;
    let socketInitialized = false;

    const setupSocket = () => {
      if (!window.frappe) {
        setSocketStatus('Waiting for Frappe...');
        return false;
      }

      if (!window.frappe.socketio) {
        setSocketStatus('Waiting for Frappe SocketIO...');
        return false;
      }

      if (!window.frappe.socketio.socket) {
        setSocketStatus('Waiting for Socket connection...');
        return false;
      }

      if (socketInitialized) {
        return true;
      }

      try {
        // Set initial connection state
        const socket = window.frappe.socketio.socket;
        setConnected(socket.connected);
        setSocketStatus(socket.connected ? 'Connected' : 'Disconnected');

        // Connection event handlers
        socket.on('connect', () => {
          console.log('Socket connected');
          setConnected(true);
          setSocketStatus('Connected');
          addMessage('system', 'Socket connected');
        });

        socket.on('disconnect', () => {
          console.log('Socket disconnected');
          setConnected(false);
          setSocketStatus('Disconnected');
          addMessage('system', 'Socket disconnected');
        });

        // Set up Frappe realtime event handlers
        if (window.frappe.realtime) {
          // THIS IS THE KEY HANDLER for plc:signal_update events
          const handleSignalUpdate = (data) => {
            console.log('RECEIVED plc:signal_update EVENT:', data);
            addMessage('plc:signal_update', data);
          };

          // THIS IS THE KEY HANDLER for plc:status events
          const handleStatusUpdate = (data) => {
            console.log('RECEIVED plc:status EVENT:', data);
            addMessage('plc:status', data);
          };

          // Register event handlers
          window.frappe.realtime.on('plc:signal_update', handleSignalUpdate);
          window.frappe.realtime.on('modbus_signal_update', handleSignalUpdate);
          window.frappe.realtime.on('plc:status', handleStatusUpdate);

          // Store handlers for cleanup
          window._signalUpdateHandler = handleSignalUpdate;
          window._statusUpdateHandler = handleStatusUpdate;

          addMessage('system', 'Event handlers registered');
          console.log('Event handlers registered successfully');
          
          // Request PLC status to test connection
          fetch('/api/method/epibus.api.plc.get_plc_status')
            .then(() => addMessage('system', 'PLC status request sent'))
            .catch(err => {
              console.error('Error requesting PLC status:', err);
              addMessage('error', `Error requesting PLC status: ${err.message}`);
            });

          socketInitialized = true;
          return true;
        } else {
          setSocketStatus('Frappe realtime not available');
          return false;
        }
      } catch (err) {
        console.error('Error setting up socket:', err);
        setError(`Error setting up socket: ${err.message}`);
        setSocketStatus(`Error: ${err.message}`);
        return false;
      }
    };

    // Try to set up socket immediately
    const success = setupSocket();

    // If not successful, check periodically
    if (!success) {
      checkInterval = setInterval(() => {
        const success = setupSocket();
        if (success) {
          clearInterval(checkInterval);
        }
      }, 1000);
    }

    // Clean up
    return () => {
      if (checkInterval) {
        clearInterval(checkInterval);
      }

      if (window.frappe?.realtime) {
        if (window._signalUpdateHandler) {
          window.frappe.realtime.off('plc:signal_update', window._signalUpdateHandler);
          window.frappe.realtime.off('modbus_signal_update', window._signalUpdateHandler);
        }
        if (window._statusUpdateHandler) {
          window.frappe.realtime.off('plc:status', window._statusUpdateHandler);
        }
      }
    };
  }, []);

  // Add a message to the list
  const addMessage = (type, data) => {
    const timestamp = new Date().toISOString();
    setMessages(prevMessages => [
      ...prevMessages,
      { type, data, timestamp }
    ]);
  };

  // Format message data as JSON
  const formatData = (data) => {
    try {
      if (typeof data === 'string') {
        return data;
      }
      return JSON.stringify(data, null, 2);
    } catch (err) {
      return `Error formatting data: ${err.message}`;
    }
  };

  return (
    <div>
      <div className="header">
        <h1>PLC Signal Monitor</h1>
        <div>
          <span className={`status ${connected ? 'connected' : 'disconnected'}`}></span>
          {socketStatus}
        </div>
      </div>

      {error && (
        <div style={{ color: 'red', marginBottom: '10px' }}>
          Error: {error}
        </div>
      )}

      <div className="message-list">
        {messages.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
            Waiting for messages...
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className="message">
              <div className="timestamp">
                [{msg.timestamp}] - {msg.type}
              </div>
              <pre>{formatData(msg.data)}</pre>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="controls">
        <button onClick={clearMessages}>
          Clear Messages
        </button>
        <button onClick={() => {
          fetch('/api/method/epibus.api.plc.get_plc_status')
            .then(() => addMessage('system', 'PLC status request sent'))
            .catch(err => addMessage('error', `Error requesting PLC status: ${err.message}`));
        }}>
          Request PLC Status
        </button>
      </div>
    </div>
  );
}

// Render the app
ReactDOM.createRoot(document.getElementById('app')).render(<App />);