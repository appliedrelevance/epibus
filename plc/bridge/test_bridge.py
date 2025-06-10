#!/usr/bin/env python3
import unittest
import time
import threading
import logging
from unittest.mock import MagicMock, patch
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

# Import the bridge module
import config
from bridge import PLCBridge, ModbusSignal

class MockResponse:
    """Mock HTTP response"""
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        
    def json(self):
        return self.json_data
        
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")

class MockModbusResponse:
    """Mock Modbus response"""
    def __init__(self, value, is_error=False):
        self.value = value
        self._is_error = is_error
        
    def isError(self):
        return self._is_error
        
    @property
    def bits(self):
        return [self.value]
        
    @property
    def registers(self):
        return [self.value]

class TestPLCBridge(unittest.TestCase):
    """Test cases for PLC Bridge"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock configuration
        self.config_patcher = patch('config.load_config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.return_value = {
            'poll_interval': 0.1,
            'log_level': 'INFO'
        }
        
        # Mock requests session
        self.session_patcher = patch('requests.Session')
        self.mock_session_class = self.session_patcher.start()
        self.mock_session = MagicMock()
        self.mock_session_class.return_value = self.mock_session
        
        # Mock ModbusTcpClient
        self.modbus_patcher = patch('bridge.ModbusTcpClient')
        self.mock_modbus_class = self.modbus_patcher.start()
        self.mock_modbus = MagicMock()
        self.mock_modbus_class.return_value = self.mock_modbus
        
        # Create bridge instance
        self.bridge = PLCBridge(
            frappe_url='http://localhost',
            api_key='test_key',
            api_secret='test_secret',
            poll_interval=0.1
        )
        
    def tearDown(self):
        """Clean up after tests"""
        self.config_patcher.stop()
        self.session_patcher.stop()
        self.modbus_patcher.stop()
        
        # Stop bridge if running
        if self.bridge.running:
            self.bridge.stop()
            
        # Clean up logging handlers to prevent resource warnings
        logger = logging.getLogger('bridge')
        if logger.hasHandlers():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
    
    def test_load_signals(self):
        """Test loading signals from Frappe"""
        # Mock API response
        mock_response = MockResponse({
            'success': True,
            'data': [
                {
                    'name': 'CONN1',
                    'host': 'localhost',
                    'port': 502,
                    'signals': [
                        {
                            'name': 'SIG1',
                            'signal_name': 'Signal 1',
                            'modbus_address': 1,
                            'signal_type': 'Digital Output Coil'
                        },
                        {
                            'name': 'SIG2',
                            'signal_name': 'Signal 2',
                            'modbus_address': 2,
                            'signal_type': 'Digital Input Contact'
                        }
                    ]
                }
            ]
        })
        self.mock_session.get.return_value = mock_response
        
        # Test loading signals
        result = self.bridge.load_signals()
        
        # Verify results
        self.assertTrue(result)
        self.assertEqual(len(self.bridge.signals), 2)
        self.assertEqual(len(self.bridge.modbus_clients), 1)
        self.assertIn('SIG1', self.bridge.signals)
        self.assertIn('SIG2', self.bridge.signals)
        self.assertIn('CONN1', self.bridge.modbus_clients)
        
    def test_read_signal_digital_input(self):
        """Test reading a digital input signal"""
        # Set up test data
        self.bridge.modbus_clients = {
            'CONN1': {
                'client': self.mock_modbus,
                'connected': True,
                'host': 'localhost',
                'port': 502
            }
        }
        signal = ModbusSignal(
            name='SIG1',
            address=1,
            signal_type='Digital Input Contact',
            signal_name='Signal 1'
        )
        
        # Mock Modbus response
        self.mock_modbus.read_discrete_inputs.return_value = MockModbusResponse(True)
        
        # Test reading signal
        value = self.bridge._read_signal('CONN1', signal)
        
        # Verify results
        self.assertTrue(value)
        self.mock_modbus.read_discrete_inputs.assert_called_once_with(address=1, count=1)
        
    def test_read_signal_digital_output(self):
        """Test reading a digital output signal"""
        # Set up test data
        self.bridge.modbus_clients = {
            'CONN1': {
                'client': self.mock_modbus,
                'connected': True,
                'host': 'localhost',
                'port': 502
            }
        }
        signal = ModbusSignal(
            name='SIG1',
            address=1,
            signal_type='Digital Output Coil',
            signal_name='Signal 1'
        )
        
        # Mock Modbus response
        self.mock_modbus.read_coils.return_value = MockModbusResponse(True)
        
        # Test reading signal
        value = self.bridge._read_signal('CONN1', signal)
        
        # Verify results
        self.assertTrue(value)
        self.mock_modbus.read_coils.assert_called_once_with(address=1, count=1)
        
    def test_read_signal_analog_input(self):
        """Test reading an analog input signal"""
        # Set up test data
        self.bridge.modbus_clients = {
            'CONN1': {
                'client': self.mock_modbus,
                'connected': True,
                'host': 'localhost',
                'port': 502
            }
        }
        signal = ModbusSignal(
            name='SIG1',
            address=1,
            signal_type='Analog Input Register',
            signal_name='Signal 1'
        )
        
        # Mock Modbus response
        self.mock_modbus.read_input_registers.return_value = MockModbusResponse(42)
        
        # Test reading signal
        value = self.bridge._read_signal('CONN1', signal)
        
        # Verify results
        self.assertEqual(value, 42)
        self.mock_modbus.read_input_registers.assert_called_once_with(address=1, count=1)
        
    def test_read_signal_holding_register(self):
        """Test reading a holding register signal"""
        # Set up test data
        self.bridge.modbus_clients = {
            'CONN1': {
                'client': self.mock_modbus,
                'connected': True,
                'host': 'localhost',
                'port': 502
            }
        }
        signal = ModbusSignal(
            name='SIG1',
            address=1,
            signal_type='Holding Register',
            signal_name='Signal 1'
        )
        
        # Mock Modbus response
        self.mock_modbus.read_holding_registers.return_value = MockModbusResponse(42)
        
        # Test reading signal
        value = self.bridge._read_signal('CONN1', signal)
        
        # Verify results
        self.assertEqual(value, 42)
        self.mock_modbus.read_holding_registers.assert_called_once_with(address=1, count=1)
        
    def test_write_signal_digital_output(self):
        """Test writing a digital output signal"""
        # Set up test data
        self.bridge.modbus_clients = {
            'CONN1': {
                'client': self.mock_modbus,
                'connected': True,
                'host': 'localhost',
                'port': 502
            }
        }
        signal = ModbusSignal(
            name='SIG1',
            address=1,
            signal_type='Digital Output Coil',
            signal_name='Signal 1'
        )
        
        # Mock Modbus response
        self.mock_modbus.write_coil.return_value = MockModbusResponse(None)
        
        # Mock publish_signal_update
        self.bridge._publish_signal_update = MagicMock()
        
        # Test writing signal
        result = self.bridge._write_signal('CONN1', signal, True)
        
        # Verify results
        self.assertTrue(result)
        self.mock_modbus.write_coil.assert_called_once_with(address=1, value=True)
        self.bridge._publish_signal_update.assert_called_once()
        
    def test_write_signal_holding_register(self):
        """Test writing a holding register signal"""
        # Set up test data
        self.bridge.modbus_clients = {
            'CONN1': {
                'client': self.mock_modbus,
                'connected': True,
                'host': 'localhost',
                'port': 502
            }
        }
        signal = ModbusSignal(
            name='SIG1',
            address=1,
            signal_type='Holding Register',
            signal_name='Signal 1'
        )
        
        # Mock Modbus response
        self.mock_modbus.write_register.return_value = MockModbusResponse(None)
        
        # Mock publish_signal_update
        self.bridge._publish_signal_update = MagicMock()
        
        # Test writing signal
        result = self.bridge._write_signal('CONN1', signal, 42)
        
        # Verify results
        self.assertTrue(result)
        self.mock_modbus.write_register.assert_called_once_with(address=1, value=42)
        self.bridge._publish_signal_update.assert_called_once()
        
    def test_publish_signal_update(self):
        """Test publishing a signal update to Frappe"""
        # Set up test data
        signal = ModbusSignal(
            name='SIG1',
            address=1,
            signal_type='Digital Output Coil',
            signal_name='Signal 1'
        )
        signal.value = True
        signal.last_update = time.time()
        
        # Mock API response
        # Mock the SSE server's publish_event method and clients
        self.bridge.sse_server.publish_event = MagicMock()
        self.bridge.sse_server.clients = {MagicMock()}

        # Test publishing update
        self.bridge._publish_signal_update(signal)

        # Verify results
        self.bridge.sse_server.publish_event.assert_called()
        
    def test_poll_signals(self):
        """Test polling signals"""
        # Set up test data
        self.bridge.modbus_clients = {
            'CONN1': {
                'client': self.mock_modbus,
                'connected': True,
                'host': 'localhost',
                'port': 502
            }
        }
        self.bridge.signals = {
            'SIG1': ModbusSignal(
                name='SIG1',
                address=1,
                signal_type='Digital Output Coil',
                signal_name='Signal 1'
            )
        }
        
        # Mock session.get for getting connection name
        mock_response = MockResponse({
            'data': {
                'parent': 'CONN1'
            }
        })
        self.mock_session.get.return_value = mock_response
        
        # Mock _read_signal
        self.bridge._read_signal = MagicMock(return_value=True)
        
        # Mock _publish_signal_update
        self.bridge._publish_signal_update = MagicMock()
        
        # Start polling in a separate thread
        self.bridge.running = True
        thread = threading.Thread(target=self.bridge._poll_signals)
        thread.daemon = True
        thread.start()
        
        # Let it run for a short time
        time.sleep(0.3)
        
        # Stop polling
        self.bridge.running = False
        thread.join(timeout=1)
        
        # Verify results
        self.bridge._read_signal.assert_called()
        self.bridge._publish_signal_update.assert_called()

if __name__ == '__main__':
    unittest.main()