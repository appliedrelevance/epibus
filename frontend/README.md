# Warehouse Dashboard React Application

A React-based dashboard for monitoring and controlling warehouse devices in the Frappe environment.

## Overview

This application provides a real-time dashboard for Modbus connections and signals. It allows users to:

- View all Modbus connections and their signals
- Filter connections by device type
- Filter signals by signal type
- Sort signals by various properties
- Toggle digital outputs
- Set values for analog outputs and holding registers
- Receive real-time updates of signal values

## Project Structure

```
frontend/
├── public/               # Static assets
├── src/                  # Source code
│   ├── components/       # React components
│   │   ├── ActionButtons.tsx       # Buttons for signal actions
│   │   ├── ConnectionCard.tsx      # Card for each Modbus connection
│   │   ├── ErrorMessage.tsx        # Error message display
│   │   ├── Filters.tsx             # Filtering controls
│   │   ├── LoadingIndicator.tsx    # Loading spinner
│   │   ├── ModbusDashboard.tsx     # Main dashboard component
│   │   ├── PollIndicator.tsx       # Polling status indicator
│   │   ├── SignalRow.tsx           # Table row for each signal
│   │   ├── SignalTable.tsx         # Table of signals
│   │   └── ValueDisplay.tsx        # Signal value display
│   ├── App.tsx           # Main App component
│   ├── index.css         # Global styles
│   ├── App.css           # App-specific styles
│   └── main.tsx          # Entry point
├── index.html            # HTML template
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
└── vite.config.ts        # Vite configuration
```

## Technology Stack

- React 18
- TypeScript
- Vite (for build and development)
- Socket.IO (for real-time updates)
- CSS (for styling)

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

1. Install dependencies:

   ```
   npm install
   ```

2. Start the development server:

   ```
   npm run start
   ```

3. Build for production:
   ```
   npm run build
   ```

## Integration with Frappe

This React application is designed to be served from the Frappe server. The build output is configured to be placed in the `public/warehouse_dashboard` directory of the Epibus app.

The application communicates with the Frappe backend through:

1. REST API endpoints for data fetching and actions
2. Socket.IO for real-time updates

## API Endpoints

- `GET /api/method/epibus.www.warehouse_dashboard.get_modbus_data` - Fetch all Modbus connections and signals
- `POST /api/method/epibus.www.warehouse_dashboard.set_signal_value` - Set a signal value

## Real-time Updates

The application uses Frappe's Socket.IO implementation to receive real-time updates for signal values. This ensures that the dashboard always displays the most current data without requiring manual refreshes.
