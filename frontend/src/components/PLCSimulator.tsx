import React, { useState, useEffect } from 'react';
import { RefreshCw, Power, ChevronDown, ChevronRight } from 'lucide-react';
import { useSimulatorAPI } from '../hooks/useSimulatorAPI';
import { useUser } from '../contexts/UserContext';
import { SignalGrid } from './signals';
import type { ModbusSimulator } from '../types/simulator';
import { useFrappeEventListener } from 'frappe-react-sdk';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

const statusColors: Record<string, string> = {
  'Running': 'text-green-500',
  'Stopped': 'text-gray-500',
  'Error': 'text-red-500',
  'Starting': 'text-yellow-500',
  'Stopping': 'text-yellow-500'
};

export const PLCSimulator: React.FC = () => {
  const { user, isLoading: userLoading } = useUser();
  const {
    simulators,
    simulatorsError,
    startSimulator,
    stopSimulator,
    refetchSimulators
  } = useSimulatorAPI();

  // Track expanded rows
  const [expandedRows, setExpandedRows] = useState<string[]>([]);

  // Listen for realtime status updates
  useFrappeEventListener('simulator_status_update', (data) => {
    console.log('🔄 Realtime status update:', data);
    refetchSimulators();
  });

  // Check status periodically
  useEffect(() => {
    console.log('⏰ Setting up status check interval');
    const interval = setInterval(() => {
      refetchSimulators();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Toggle row expansion
  const toggleRow = (simulatorId: string) => {
    setExpandedRows(current =>
      current.includes(simulatorId)
        ? current.filter(id => id !== simulatorId)
        : [...current, simulatorId]
    );
  };

  // Handle signal value changes
  const handleSignalChange = (simulator: ModbusSimulator, signalName: string, value: number | boolean) => {
    console.log(`🎛️ Signal change on ${simulator.name}: ${signalName} = ${value}`);
    // TODO: Implement signal value update via API
  };

  if (userLoading) {
    return <div className="flex justify-center p-8">Loading...</div>;
  }

  if (!user) {
    return (
      <div className="text-red-500 p-8">
        Please log in to view PLC simulators
      </div>
    );
  }

  if (simulatorsError) {
    return (
      <div className="text-red-500 p-8">
        {simulatorsError.message || 'An error occurred loading simulators'}
      </div>
    );
  }

  const handleSimulatorAction = (name: string, status: string) => {
    console.log(`🎮 ${status === 'Running' ? 'Stopping' : 'Starting'} simulator:`, name);

    const action = status === 'Running' ? stopSimulator : startSimulator;
    action(name)
      .then(() => {
        console.log(`✅ Action successful for ${name}`);
        refetchSimulators();
      })
      .catch((err) => {
        console.error(`❌ Error with simulator action:`, err);
      });
  };

  const handleRefresh = () => {
    console.log('🔄 Manual refresh triggered');
    refetchSimulators();
  };

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>PLC Simulators</CardTitle>
        <Button
          variant="outline"
          size="icon"
          onClick={handleRefresh}
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="text-sm text-muted-foreground mb-4">
          Logged in as: <span className="font-medium">{String(user)}</span>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8"></TableHead>
              <TableHead>ID</TableHead>
              <TableHead>Simulator Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Port</TableHead>
              <TableHead>Equipment Type</TableHead>
              <TableHead>Last Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {simulators.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center text-muted-foreground"
                >
                  No simulators configured
                </TableCell>
              </TableRow>
            ) : (
              simulators.map((simulator) => (
                <React.Fragment key={simulator.name}>
                  <TableRow>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => toggleRow(simulator.name)}
                      >
                        {expandedRows.includes(simulator.name) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell>{simulator.name}</TableCell>
                    <TableCell className="font-medium">
                      {simulator.simulator_name}
                    </TableCell>
                    <TableCell>
                      <span className={statusColors[simulator.server_status]}>
                        {simulator.server_status}
                      </span>
                    </TableCell>
                    <TableCell>{simulator.server_port}</TableCell>
                    <TableCell>{simulator.equipment_type}</TableCell>
                    <TableCell>
                      {new Date(simulator.last_status_update).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant={simulator.server_status === 'Running' ? 'destructive' : 'default'}
                        onClick={() => handleSimulatorAction(
                          simulator.name,
                          simulator.server_status
                        )}
                        disabled={!simulator.enabled}
                      >
                        <Power className="h-4 w-4 mr-1" />
                        {simulator.server_status === 'Running' ? 'Stop' : 'Start'}
                      </Button>
                    </TableCell>
                  </TableRow>
                  {expandedRows.includes(simulator.name) && (
                    <TableRow>
                      <TableCell colSpan={8} className="p-0">
                        <div className="bg-muted/50 border-y">
                          <SignalGrid
                            signals={simulator.io_points}
                            onSignalChange={(signalName, value) =>
                              handleSignalChange(simulator, signalName, value)
                            }
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default PLCSimulator;