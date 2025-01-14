import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { AlertCircle, Power, PowerOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSimulatorAPI } from '@/hooks/useSimulatorAPI';
import type { Simulator } from '@/types/simulator';

export function PLCSimulator(): React.ReactElement {
  const { 
    simulators, 
    simulatorsError, 
    startSimulator, 
    stopSimulator 
  } = useSimulatorAPI();

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
      <div className="container mx-auto p-6 font-georama">
        <Card className="border-red-200 shadow-md">
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle className="w-5 h-5" />
              <span>Failed to fetch simulators: {simulatorsError.message}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!simulators?.length) {
    return (
      <div className="container mx-auto p-6 font-georama">
        <Card className="shadow-md">
          <CardContent className="p-6">
            <div className="text-center">
              <h3 className="text-lg font-medium mb-2">No Simulators Found</h3>
              <p className="text-muted-foreground">No PLC simulators are currently configured.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 font-georama">
      <Card className="shadow-lg">
        <CardHeader className="pb-3 bg-slate-50 rounded-t-lg border-b">
          <CardTitle className="text-2xl font-semibold tracking-tight">
            PLC Simulators
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="rounded-md border border-slate-200">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead className="w-[200px] font-georama font-semibold">Name</TableHead>
                  <TableHead className="font-georama font-semibold">Status</TableHead>
                  <TableHead className="font-georama font-semibold">Port</TableHead>
                  <TableHead className="font-georama font-semibold">Enabled</TableHead>
                  <TableHead className="w-[180px] font-georama font-semibold">Last Updated</TableHead>
                  <TableHead className="text-right font-georama font-semibold">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {simulators.map((simulator) => (
                  <TableRow key={simulator.name} className="hover:bg-slate-50/50">
                    <TableCell className="font-medium">{simulator.name}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span 
                          className={`h-2.5 w-2.5 rounded-full ${
                            simulator.connection_status === 'Connected' 
                              ? 'bg-green-500 animate-pulse' 
                              : simulator.connection_status === 'Error'
                              ? 'bg-red-500'
                              : 'bg-yellow-500'
                          }`}
                        />
                        <span className="text-sm">{simulator.connection_status}</span>
                      </div>
                    </TableCell>
                    <TableCell>{simulator.server_port}</TableCell>
                    <TableCell>
                      <span className={`${
                        simulator.enabled 
                          ? 'text-green-600 font-medium' 
                          : 'text-slate-500'
                      }`}>
                        {simulator.enabled ? 'Yes' : 'No'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-slate-600">
                        {new Date(simulator.last_status_update).toLocaleString()}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      {simulator.connection_status === 'Connected' ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => void handleStop(simulator)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50 transition-colors"
                        >
                          <PowerOff className="w-4 h-4 mr-2" />
                          Stop
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => void handleStart(simulator)}
                          disabled={!simulator.enabled}
                          className="text-green-600 hover:text-green-700 hover:bg-green-50 transition-colors"
                        >
                          <Power className="w-4 h-4 mr-2" />
                          Start
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default PLCSimulator;