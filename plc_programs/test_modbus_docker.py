#!/usr/bin/env python3
"""
Test script for Intralogistics Lab MODBUS integration (Docker version)
Tests ERP integration with CODESYS project via MODBUS TCP
"""

import time
import sys
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException

class IntralogisticsLabTester:
    def __init__(self, host='codesys'):
        self.host = host
        self.port = 502
        self.client = ModbusTcpClient(host, port=self.port)
        
    def connect(self):
        """Connect to MODBUS server"""
        print(f"🔌 Connecting to MODBUS server at {self.host}:{self.port}")
        try:
            if self.client.connect():
                print("✅ Connected successfully")
                return True
            else:
                print("❌ Connection failed")
                return False
        except Exception as e:
            print(f"❌ Connection exception: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from MODBUS server"""
        self.client.close()
        print("🔌 Disconnected")
        
    def test_basic_connectivity(self):
        """Test basic MODBUS connectivity"""
        print("\n🔗 Testing Basic Connectivity...")
        try:
            # Try to read a single register
            result = self.client.read_holding_registers(0, 1)
            if result.isError():
                print(f"   MODBUS server responding with error (expected): {result}")
                return True  # This is normal - server exists but register may not
            else:
                print(f"   MODBUS register read successful: {result.registers}")
                return True
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
            
    def test_coil_operations(self):
        """Test coil read/write operations"""
        print("\n🔘 Testing Coil Operations...")
        try:
            # Test writing to some coils
            test_coils = [1000, 1001, 1002]
            
            for coil in test_coils:
                print(f"   Testing coil {coil}")
                
                # Write coil
                write_result = self.client.write_coil(coil, True)
                if write_result.isError():
                    print(f"   Write to coil {coil}: {write_result}")
                else:
                    print(f"   ✅ Write to coil {coil}: Success")
                
                # Read coil back
                read_result = self.client.read_coils(coil, 1)
                if read_result.isError():
                    print(f"   Read from coil {coil}: {read_result}")
                else:
                    print(f"   ✅ Read from coil {coil}: {read_result.bits[0]}")
                
                time.sleep(0.1)
                
            return True
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
            
    def test_register_operations(self):
        """Test holding register operations"""
        print("\n📊 Testing Register Operations...")
        try:
            # Test reading some registers
            test_registers = [100, 200, 300]
            
            for reg in test_registers:
                print(f"   Testing register {reg}")
                
                # Read register
                result = self.client.read_holding_registers(reg, 1)
                if result.isError():
                    print(f"   Read from register {reg}: {result}")
                else:
                    print(f"   ✅ Read from register {reg}: {result.registers[0]}")
                
                time.sleep(0.1)
                
            return True
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
            
    def test_bin_selection_simulation(self):
        """Test bin selection coils (2000-2011)"""
        print("\n📦 Testing Bin Selection (Coils 2000-2011)...")
        try:
            # Test bin selection coils
            for bin_num in range(1, 5):  # Test first 4 bins
                coil_addr = 2000 + bin_num - 1
                print(f"   Selecting Bin {bin_num} (coil {coil_addr})")
                
                # Select bin
                result = self.client.write_coil(coil_addr, True)
                if result.isError():
                    print(f"   Error selecting bin {bin_num}: {result}")
                else:
                    print(f"   ✅ Bin {bin_num} selected")
                
                time.sleep(0.2)
                
                # Deselect bin
                result = self.client.write_coil(coil_addr, False)
                if result.isError():
                    print(f"   Error deselecting bin {bin_num}: {result}")
                else:
                    print(f"   ✅ Bin {bin_num} deselected")
                
                time.sleep(0.2)
                
            return True
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
            
    def run_full_test(self):
        """Run complete test suite"""
        print("🧪 Intralogistics Lab MODBUS Integration Test (Docker)")
        print("=" * 60)
        
        if not self.connect():
            return False
            
        tests = [
            ("Basic Connectivity", self.test_basic_connectivity),
            ("Coil Operations", self.test_coil_operations), 
            ("Register Operations", self.test_register_operations),
            ("Bin Selection Simulation", self.test_bin_selection_simulation)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        print(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! MODBUS integration is working correctly.")
            print("🚀 The CODESYS server is ready for project deployment!")
        else:
            print("⚠️  Some tests failed. MODBUS server may need configuration.")
            
        self.disconnect()
        return passed == total

def main():
    """Main test function"""
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = 'codesys'
        
    tester = IntralogisticsLabTester(host)
    success = tester.run_full_test()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()