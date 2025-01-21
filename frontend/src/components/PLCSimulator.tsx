import React from 'react';
import { RefreshCw, Power } from 'lucide-react';
import { useSimulatorAPI } from '../hooks/useSimulatorAPI';
import { useUser } from '../contexts/UserContext';

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

  console.log('📊 Current simulators:', simulators);

  if (userLoading) {
    return <div className="flex justify-center p-8">Loading...</div>;
  }

  // Make sure we handle the case when user might be null
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

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>PLC Simulators</CardTitle>
        <Button
          variant="outline"
          size="icon"
          onClick={() => refetchSimulators()}
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
                  colSpan={6}
                  className="text-center text-muted-foreground"
                >
                  No simulators configured
                </TableCell>
              </TableRow>
            ) : (
              simulators.map((simulator) => (
                <TableRow key={simulator.name}>
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
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default PLCSimulator;