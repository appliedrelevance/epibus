import React from 'react';
import { Power, RotateCw } from 'lucide-react';
import { useSimulatorAPI } from '../hooks/useSimulatorAPI';
import { useUser } from '../contexts/UserContext';
import type { ModbusSimulator, ServerStatus } from '../types/simulator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';

const statusColors: Record<ServerStatus, string> = {
  'Running': 'text-green-500',
  'Stopped': 'text-gray-500',
  'Starting': 'text-yellow-500',
  'Stopping': 'text-yellow-500',
  'Error': 'text-red-500'
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

  const handleAction = (simulator: ModbusSimulator) => {
    console.log(`🎮 Processing action for ${simulator.simulator_name}`);
    const isRunning = simulator.server_status === 'Running';

    const actionFn = isRunning ? stopSimulator : startSimulator;
    actionFn(simulator.name)
      .then(() => {
        console.log(`✅ ${isRunning ? 'Stop' : 'Start'} successful for ${simulator.name}`);
        refetchSimulators();
      })
      .catch((err) => {
        console.error(`❌ Action failed:`, err);
      });
  };

  if (userLoading) return <div>Loading...</div>;
  if (!user) return <div>Please log in to view simulators</div>;
  if (simulatorsError) return <div>Error: {simulatorsError instanceof Error ? simulatorsError.message : String(simulatorsError)}</div>;

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold">PLC Simulators</h1>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              console.log('🔄 Refreshing simulators');
              refetchSimulators();
            }}
          >
            <RotateCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Port</TableHead>
              <TableHead>Equipment Type</TableHead>
              <TableHead>Last Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {!simulators?.length ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center">
                  No simulators configured
                </TableCell>
              </TableRow>
            ) : (
              simulators.map((simulator) => (
                <TableRow key={simulator.name}>
                  <TableCell>{simulator.simulator_name}</TableCell>
                  <TableCell>
                    <span className={statusColors[simulator.server_status]}>
                      {simulator.server_status}
                      {simulator.error_message && (
                        <span className="ml-2 text-xs text-red-500">
                          ({simulator.error_message})
                        </span>
                      )}
                    </span>
                  </TableCell>
                  <TableCell>{simulator.server_port}</TableCell>
                  <TableCell>{simulator.equipment_type || 'Unknown'}</TableCell>
                  <TableCell>
                    {new Date(simulator.last_status_update).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant={simulator.server_status === 'Running' ? 'destructive' : 'default'}
                      onClick={() => handleAction(simulator)}
                      disabled={!simulator.enabled}
                    >
                      <Power className="h-4 w-4 mr-2" />
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