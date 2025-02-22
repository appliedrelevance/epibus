from pymodbus.client import ModbusTcpClient
import asyncio

def print_help():
    print("\nAvailable commands:")
    print("read_coil <address> - Read single coil")
    print("read_coils <address> <count> - Read multiple coils")
    print("read_holding <address> - Read single holding register")
    print("read_holdings <address> <count> - Read multiple holding registers")
    print("write_coil <address> <value> - Write to coil (0/1)")
    print("write_holding <address> <value> - Write to holding register")
    print("help - Show this help")
    print("exit - Exit the client\n")

def main():
    client = ModbusTcpClient('openplc', port=502)
    if not client.connect():
        print("Failed to connect!")
        return

    print("\nConnected to OpenPLC at openplc:502")
    print_help()

    try:
        while True:
            cmd = input("\nmodbus> ").strip().split()
            if not cmd:
                continue

            if cmd[0] == "exit":
                break
            elif cmd[0] == "help":
                print_help()
            elif cmd[0] == "read_coil" and len(cmd) == 2:
                result = client.read_coils(address=int(cmd[1]), count=1)
                if result.isError():
                    print(f"Error: {result}")
                else:
                    print(f"Coil {cmd[1]}: {result.bits[0]}")
            elif cmd[0] == "read_coils" and len(cmd) == 3:
                result = client.read_coils(address=int(cmd[1]), count=int(cmd[2]))
                if result.isError():
                    print(f"Error: {result}")
                else:
                    print(f"Coils {cmd[1]}-{int(cmd[1])+int(cmd[2])-1}: {result.bits}")
            elif cmd[0] == "read_holding" and len(cmd) == 2:
                result = client.read_holding_registers(address=int(cmd[1]), count=1)
                if result.isError():
                    print(f"Error: {result}")
                else:
                    print(f"Register {cmd[1]}: {result.registers[0]}")
            elif cmd[0] == "read_holdings" and len(cmd) == 3:
                result = client.read_holding_registers(address=int(cmd[1]), count=int(cmd[2]))
                if result.isError():
                    print(f"Error: {result}")
                else:
                    print(f"Registers {cmd[1]}-{int(cmd[1])+int(cmd[2])-1}: {result.registers}")
            elif cmd[0] == "write_coil" and len(cmd) == 3:
                result = client.write_coil(address=int(cmd[1]), value=int(cmd[2]) == 1)
                if result.isError():
                    print(f"Error: {result}")
                else:
                    print(f"Written {cmd[2]} to coil {cmd[1]}")
            elif cmd[0] == "write_holding" and len(cmd) == 3:
                result = client.write_register(address=int(cmd[1]), value=int(cmd[2]))
                if result.isError():
                    print(f"Error: {result}")
                else:
                    print(f"Written {cmd[2]} to register {cmd[1]}")
            else:
                print("Invalid command or arguments")
                print_help()

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        client.close()

if __name__ == '__main__':
    main()
