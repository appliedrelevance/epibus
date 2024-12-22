import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { AlertCircle } from 'lucide-react';
import { useSimulatorAPI } from '@/hooks/useSimulatorAPI';
import type { Simulator } from '@/types/simulator';

export function PLCSimulator(): React.ReactElement {
  const { 
    simulators, 
    simulatorsError, 
    startSimulator, 
    stopSimulator 
  } = useSimulatorAPI();

  console.log('simulators from hook', simulators);
  console.log('simulatorsError from hook', simulatorsError);

  const handleStart = async (simulator: Simulator): Promise<void> => {
    try {
      await startSimulator(simulator.name);
    } catch (error) {
      console.error('Failed to start simulator:', error);
    }
  };

  const handleStop = async (simulator: Simulator): Promise<void> => {
    try {
      await stopSimulator(simulator.name);
    } catch (error) {
      console.error('Failed to stop simulator:', error);
    }
  };

  if (simulatorsError) {
    return (
      <Card className="border-red-200">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-red-600">
            <AlertCircle className="w-5 h-5" />
            <span>Failed to fetch simulators: {simulatorsError.message}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!simulators?.length) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">
            <h3 className="text-lg font-medium mb-2">No Simulators Found</h3>
            <p className="text-gray-500 mb-4">No PLC simulators are currently configured.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-6">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Port</TableHead>
              <TableHead>Enabled</TableHead>
              <TableHead>Last Updated</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {simulators.map((simulator) => (
              <TableRow key={simulator.name}>
                <TableCell className="font-medium">{simulator.name}</TableCell>
                <TableCell>
                  <div className="flex items-center">
                    <span 
                      className={`w-2 h-2 rounded-full mr-2 ${
                        simulator.connection_status === 'Connected' 
                          ? 'bg-green-500' 
                          : simulator.connection_status === 'Error'
                          ? 'bg-red-500'
                          : 'bg-gray-500'
                      }`}
                    />
                    {simulator.connection_status}
                  </div>
                </TableCell>
                <TableCell>{simulator.server_port}</TableCell>
                <TableCell>
                  {simulator.enabled ? (
                    <span className="text-green-600">Yes</span>
                  ) : (
                    <span className="text-gray-500">No</span>
                  )}
                </TableCell>
                <TableCell>
                  {new Date(simulator.last_status_update).toLocaleString()}
                </TableCell>
                <TableCell>
                  {simulator.connection_status === 'Connected' ? (
                    <button
                      onClick={() => void handleStop(simulator)}
                      className="text-red-600 hover:text-red-800"
                      type="button"
                    >
                      Stop
                    </button>
                  ) : (
                    <button
                      onClick={() => void handleStart(simulator)}
                      className="text-green-600 hover:text-green-800"
                      disabled={!simulator.enabled}
                      type="button"
                    >
                      Start
                    </button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export default PLCSimulator;