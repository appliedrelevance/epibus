// components/PLCSimulator.tsx
import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Slider } from '@/components/ui/slider'
import { Power, XCircle, AlertCircle, Activity } from 'lucide-react'
import { useSimulator } from '@/hooks/useSimulator'

export const PLCSimulator: React.FC = () => {
  const { isConnected, ioPoints, error, connect, disconnect, togglePoint, setValue } = useSimulator()
  const [selectedTab, setSelectedTab] = useState('digital')

  const handleConnect = async () => {
    if (isConnected) {
      await disconnect()
    } else {
      await connect()
    }
  }

  const handleToggle = async (address: number, type: string) => {
    await togglePoint(address, type)
  }

  const handleSliderChange = async (address: number, values: number[]) => {
    await setValue(address, 'register', values[0])
  }

  const filteredPoints = ioPoints.filter(point => {
    switch (selectedTab) {
      case 'digital':
        return point.type === 'input' || point.type === 'output'
      case 'analog':
        return point.type === 'register' && point.name.toLowerCase().includes('analog')
      case 'registers':
        return point.type === 'register' && !point.name.toLowerCase().includes('analog')
      default:
        return false
    }
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">PLC Simulator</h1>
        <div className="flex items-center gap-4">
          {isConnected && (
            <div className="flex items-center text-green-500">
              <Activity className="w-4 h-4 animate-pulse mr-2" />
              <span className="text-sm">Connected</span>
            </div>
          )}
          <Button
            variant={isConnected ? "destructive" : "default"}
            onClick={handleConnect}
          >
            {isConnected ? (
              <>
                <XCircle className="mr-2 h-4 w-4" />
                Disconnect
              </>
            ) : (
              <>
                <Power className="mr-2 h-4 w-4" />
                Connect
              </>
            )}
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            <ToggleGroup type="single" value={selectedTab} onValueChange={setSelectedTab} className="justify-start">
              <ToggleGroupItem value="digital" className="px-4">
                Digital I/O
              </ToggleGroupItem>
              <ToggleGroupItem value="analog" className="px-4">
                Analog I/O
              </ToggleGroupItem>
              <ToggleGroupItem value="registers" className="px-4">
                Registers
              </ToggleGroupItem>
            </ToggleGroup>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Address</TableHead>
                  <TableHead>PLC Address</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPoints.map((point) => (
                  <TableRow key={`${point.type}-${point.address}`}>
                    <TableCell>{point.name}</TableCell>
                    <TableCell>{point.address}</TableCell>
                    <TableCell>{point.plc_address}</TableCell>
                    <TableCell className="capitalize">{point.type}</TableCell>
                    <TableCell>
                      {typeof point.value === 'boolean' 
                        ? point.value ? 'ON' : 'OFF'
                        : point.value}
                    </TableCell>
                    <TableCell>
                      {point.type === 'register' ? (
                        <div className="w-32">
                          <Slider
                            defaultValue={[point.value as number]}
                            min={0}
                            max={65535}
                            step={1}
                            onValueChange={(values) => handleSliderChange(point.address, values)}
                            disabled={!isConnected}
                          />
                        </div>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggle(point.address, point.type)}
                          disabled={!isConnected || point.type === 'input'}
                        >
                          Toggle
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

      {error && (
        <div className="flex items-center space-x-2 text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}