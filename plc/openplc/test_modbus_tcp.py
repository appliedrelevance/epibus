from pymodbus.client import ModbusTcpClient
import logging

# Enable debug logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def test_dns_resolution(host):
    """Test DNS resolution of the host"""
    import socket
    print(f"\n🔍 Testing DNS resolution for {host}...")
    try:
        ip = socket.gethostbyname(host)
        print(f"✅ DNS Resolution successful: {host} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS Resolution failed: {str(e)}")
        return False


def test_modbus_connection():
    # Use the Docker service name as hostname
    host = 'openplc'
    port = 502

    print(f"🔌 Testing MODBUS TCP connection to {host}:{port}...")

    # Test DNS resolution first
    if not test_dns_resolution(host):
        print("❌ Cannot resolve hostname. Check Docker network configuration.")
        return

    # Create a client
    client = ModbusTcpClient(host, port=port)

    try:
        # Try to connect with a shorter timeout
        client.timeout = 2
        connection = client.connect()
        print(
            f"📡 Connection status: {'✅ Connected' if connection else '❌ Failed'}")

        if connection:
            # Try reading some coils (digital outputs)
            print("\n🔍 Reading first 8 coils...")
            result = client.read_coils(address=0, count=8)
            if hasattr(result, 'bits'):
                print("✅ Coil values:", result.bits)
            else:
                print("❌ Failed to read coils:", result)

            # Try reading discrete inputs
            print("\n🔍 Reading first 8 discrete inputs...")
            result = client.read_discrete_inputs(address=0, count=8)
            if hasattr(result, 'bits'):
                print("✅ Input values:", result.bits)
            else:
                print("❌ Failed to read inputs:", result)

            # Try writing to a coil
            print("\n📝 Writing TRUE to first coil...")
            result = client.write_coil(address=0, value=True)
            if result:
                print("✅ Write successful")

                # Read back the value to verify
                verify = client.read_coils(address=0, count=1)
                if hasattr(verify, 'bits'):
                    print(f"✅ Verified value: {verify.bits[0]}")
            else:
                print("❌ Write failed:", result)

    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")

    finally:
        # Always close the connection
        client.close()
        print("\n👋 Connection closed")


if __name__ == "__main__":
    test_modbus_connection()
