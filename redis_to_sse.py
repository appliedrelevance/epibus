#!/usr/bin/env python3
"""
Redis to Server-Sent Events (SSE) Bridge

This script creates a direct bridge between Redis and a web browser using Server-Sent Events (SSE).
It's a simpler alternative to Socket.IO that works in all modern browsers.

Usage:
    python redis_to_sse.py [--redis-host HOSTNAME] [--redis-port PORT] [--http-port PORT]

Options:
    --redis-host HOSTNAME    Redis hostname [default: 127.0.0.1]
    --redis-port PORT        Redis port [default: 11000]
    --http-port PORT         HTTP server port [default: 12345]
"""

import redis
import json
import argparse
import time
import sys
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import urllib.parse
import queue

# Global variables
redis_client = None
pubsub = None
running = True
clients = []  # List of client queues
client_lock = threading.Lock()

class SSEHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Serve the SSE stream
        if parsed_path.path == '/events':
            self.send_sse_response()
        # Serve the HTML page
        elif parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.send_html_response()
        # Handle other requests
        else:
            self.send_error(404, "Not Found")
    
    def send_sse_response(self):
        """Send Server-Sent Events response"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Create a queue for this client
        client_queue = queue.Queue()
        
        # Add client to the list
        with client_lock:
            clients.append(client_queue)
        
        print(f"Client connected: {self.client_address}")
        
        try:
            # Send initial connection message
            self.send_sse_event({
                'type': 'connection_status',
                'data': {
                    'status': 'connected',
                    'timestamp': time.time()
                }
            })
            
            # Keep the connection open and send events as they arrive
            while running:
                try:
                    # Get event from queue with timeout
                    event = client_queue.get(timeout=1)
                    self.send_sse_event(event)
                except queue.Empty:
                    # Send a heartbeat every 10 seconds
                    self.send_sse_event({
                        'type': 'heartbeat',
                        'data': {
                            'timestamp': time.time()
                        }
                    })
                    time.sleep(10)
        except (BrokenPipeError, ConnectionResetError):
            print(f"Client disconnected: {self.client_address}")
        finally:
            # Remove client from the list
            with client_lock:
                if client_queue in clients:
                    clients.remove(client_queue)
    
    def send_sse_event(self, event_data):
        """Send a Server-Sent Event"""
        try:
            data_str = json.dumps(event_data)
            self.wfile.write(f"data: {data_str}\n\n".encode('utf-8'))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            raise
    
    def send_html_response(self):
        """Send HTML response"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        
        # Simple HTML page with embedded JavaScript for SSE
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Redis SSE Monitor</title>
  <style>
    body {
      font-family: monospace;
      margin: 20px;
      background-color: #f5f5f5;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
    }
    .header {
      background-color: #333;
      color: white;
      padding: 10px;
      margin-bottom: 10px;
      border-radius: 4px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .status {
      display: inline-block;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      margin-right: 8px;
    }
    .connected {
      background-color: #4CAF50;
    }
    .disconnected {
      background-color: #F44336;
    }
    .message-list {
      height: 600px;
      overflow-y: auto;
      border: 1px solid #ddd;
      padding: 10px;
      background-color: white;
      border-radius: 4px;
    }
    .message {
      margin-bottom: 8px;
      padding: 8px;
      border-bottom: 1px solid #eee;
    }
    .message pre {
      margin: 5px 0;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
    .timestamp {
      color: #666;
      font-size: 0.8em;
    }
    .controls {
      margin-top: 10px;
      display: flex;
      gap: 10px;
    }
    button {
      padding: 8px 16px;
      background-color: #4CAF50;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    button:hover {
      background-color: #45a049;
    }
    .plc-signal {
      background-color: #e6f7ff;
    }
    .plc-status {
      background-color: #f0f7ff;
    }
    .plc-command {
      background-color: #fff7e6;
    }
    .system {
      background-color: #f9f9f9;
    }
    .error {
      background-color: #fff1f0;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Redis SSE Monitor</h1>
      <div>
        <span id="status-indicator" class="status disconnected"></span>
        <span id="status-text">Connecting...</span>
      </div>
    </div>

    <div id="error-container" style="color: red; margin-bottom: 10px; padding: 10px; background-color: #ffeeee; border-radius: 4px; display: none;"></div>

    <div class="message-list" id="message-list">
      <div style="padding: 20px; text-align: center; color: #666;">
        Waiting for messages...
      </div>
    </div>
    
    <div class="controls">
      <button id="clear-btn">Clear Messages</button>
    </div>
  </div>

  <script>
    // DOM Elements
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const messageList = document.getElementById('message-list');
    const errorContainer = document.getElementById('error-container');
    const clearBtn = document.getElementById('clear-btn');
    
    // State
    let connected = false;
    let messages = [];
    let eventSource = null;
    
    // Initialize
    function init() {
      clearBtn.addEventListener('click', clearMessages);
      connectEventSource();
    }
    
    // Connect to SSE
    function connectEventSource() {
      // Close existing connection if any
      if (eventSource) {
        eventSource.close();
      }
      
      try {
        // Create new EventSource connection
        eventSource = new EventSource('/events');
        
        // EventSource event handlers
        eventSource.onopen = function() {
          console.log('SSE connection opened');
          updateStatus('Connected', true);
        };
        
        eventSource.onerror = function(err) {
          console.error('SSE error:', err);
          updateStatus('Connection Error', false);
          showError('Connection error - check server');
        };
        
        eventSource.onmessage = function(event) {
          console.log('SSE message received:', event.data);
          try {
            const data = JSON.parse(event.data);
            if (data && data.type) {
              addMessage(data.type, data.data);
              
              // Update connection status if it's a connection_status event
              if (data.type === 'connection_status') {
                updateStatus('Connected', true);
              }
            }
          } catch (err) {
            console.error('Error parsing SSE message:', err);
            addMessage('error', 'Error parsing message: ' + event.data);
          }
        };
      } catch (err) {
        console.error('Error connecting to SSE:', err);
        updateStatus('Connection Error', false);
        showError('Error connecting to SSE: ' + err.message);
      }
    }
    
    // Update connection status
    function updateStatus(text, isConnected) {
      statusText.textContent = text;
      statusIndicator.className = `status ${isConnected ? 'connected' : 'disconnected'}`;
      connected = isConnected;
    }
    
    // Show error message
    function showError(message) {
      if (message) {
        errorContainer.textContent = `Error: ${message}`;
        errorContainer.style.display = 'block';
      } else {
        errorContainer.textContent = '';
        errorContainer.style.display = 'none';
      }
    }
    
    // Add a message to the list
    function addMessage(type, data) {
      const timestamp = new Date().toISOString();
      messages.push({ type, data, timestamp });
      
      // Update UI
      renderMessages();
    }
    
    // Clear messages
    function clearMessages() {
      messages = [];
      renderMessages();
    }
    
    // Render messages
    function renderMessages() {
      if (messages.length === 0) {
        messageList.innerHTML = `
          <div style="padding: 20px; text-align: center; color: #666;">
            Waiting for messages...
          </div>
        `;
        return;
      }
      
      messageList.innerHTML = messages.map((msg, index) => `
        <div class="message ${msg.type}">
          <div class="timestamp">
            [${msg.timestamp}] - ${msg.type}
          </div>
          <pre>${formatData(msg.data)}</pre>
        </div>
      `).join('');
      
      // Scroll to bottom
      messageList.scrollTop = messageList.scrollHeight;
    }
    
    // Format message data as JSON
    function formatData(data) {
      try {
        if (typeof data === 'string') {
          return data;
        }
        return JSON.stringify(data, null, 2);
      } catch (err) {
        return `Error formatting data: ${err.message}`;
      }
    }
    
    // Initialize when the page loads
    window.addEventListener('load', init);
  </script>
</body>
</html>
        """
        
        self.wfile.write(html.encode('utf-8'))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass

def redis_listener(host='127.0.0.1', port=11000):
    """Listen for Redis messages and forward to clients"""
    global redis_client, pubsub, running
    
    try:
        # Connect to Redis
        redis_client = redis.Redis(host=host, port=port, db=0)
        pubsub = redis_client.pubsub()
        
        # Subscribe to channels
        channels = ['plc:signal_update', 'plc:command', 'plc:status']
        pubsub.subscribe(channels)
        
        print(f"Connected to Redis at {host}:{port}")
        print(f"Monitoring channels: {', '.join(channels)}")
        
        # Process messages
        for message in pubsub.listen():
            if not running:
                break
                
            if message['type'] == 'message':
                channel = message['channel']
                data = message['data']
                
                # Convert bytes to string if needed
                if isinstance(channel, bytes):
                    channel = channel.decode('utf-8')
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                
                # Parse JSON data
                try:
                    json_data = json.loads(data)
                except:
                    json_data = data
                
                # Create event
                event = {
                    'type': channel,
                    'data': json_data,
                    'timestamp': time.time()
                }
                
                # Forward to all clients
                with client_lock:
                    client_count = len(clients)
                    print(f"Forwarding {channel} message to {client_count} clients: {data[:100]}...")
                    
                    for client_queue in clients:
                        client_queue.put(event)
                
    except Exception as e:
        print(f"Redis listener error: {e}")
    finally:
        # Clean up
        if pubsub:
            try:
                pubsub.unsubscribe()
                pubsub.close()
            except:
                pass

def start_server(redis_host='127.0.0.1', redis_port=11000, http_port=12345):
    """Start the HTTP server and Redis listener"""
    global running
    
    # Start Redis listener in a separate thread
    redis_thread = threading.Thread(
        target=redis_listener, 
        args=(redis_host, redis_port),
        daemon=True
    )
    redis_thread.start()
    
    # Start HTTP server
    server_address = ('', http_port)
    httpd = ThreadedHTTPServer(server_address, SSEHandler)
    
    print(f"Starting HTTP server on port {http_port}")
    print(f"Open http://localhost:{http_port}/ in your browser")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        running = False
        httpd.server_close()
        # Wait for Redis thread to finish
        redis_thread.join(timeout=1.0)
        print("Server stopped")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Redis to SSE Bridge")
    parser.add_argument("--redis-host", default="127.0.0.1", help="Redis hostname")
    parser.add_argument("--redis-port", type=int, default=11000, help="Redis port")
    parser.add_argument("--http-port", type=int, default=12345, help="HTTP server port")
    args = parser.parse_args()
    
    # Start server
    start_server(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        http_port=args.http_port
    )