#include <stdio.h>
#include </usr/include/modbus/modbus.h>
#include <errno.h>
#include <string.h>

void test_holding_registers(modbus_t *ctx)
{
    uint16_t reg[10];
    int rc;

    printf("\n=== Testing Holding Registers ===\n");

    // Write value to register 0
    uint16_t write_value = 12345;
    printf("Writing value %d to register 0\n", write_value);
    rc = modbus_write_register(ctx, 0, write_value);
    if (rc == -1)
    {
        fprintf(stderr, "Write failed: %s\n", modbus_strerror(errno));
        return;
    }

    // Read back the value
    printf("Reading register 0\n");
    rc = modbus_read_registers(ctx, 0, 1, reg);
    if (rc == -1)
    {
        fprintf(stderr, "Read failed: %s\n", modbus_strerror(errno));
        return;
    }
    printf("Register 0 = %d (0x%X)\n", reg[0], reg[0]);
}

void test_coils(modbus_t *ctx)
{
    uint8_t coil_value;
    int rc;

    printf("\n=== Testing Coils ===\n");

    // Write TRUE to coil 0
    printf("Writing TRUE to coil 0\n");
    rc = modbus_write_bit(ctx, 0, TRUE);
    if (rc == -1)
    {
        fprintf(stderr, "Write coil failed: %s\n", modbus_strerror(errno));
        return;
    }

    // Read back the coil
    printf("Reading coil 0\n");
    rc = modbus_read_bits(ctx, 0, 1, &coil_value);
    if (rc == -1)
    {
        fprintf(stderr, "Read coil failed: %s\n", modbus_strerror(errno));
        return;
    }
    printf("Coil 0 = %s\n", coil_value ? "TRUE" : "FALSE");
}

void test_input_registers(modbus_t *ctx)
{
    uint16_t reg[10];
    int rc;

    printf("\n=== Testing Input Registers ===\n");

    rc = modbus_read_input_registers(ctx, 0, 10, reg);
    if (rc == -1)
    {
        fprintf(stderr, "Read input registers failed: %s\n", modbus_strerror(errno));
        return;
    }

    printf("First 10 input registers:\n");
    for (int i = 0; i < rc; i++)
    {
        printf("reg[%d]=%d (0x%X)\n", i, reg[i], reg[i]);
    }
}

int main()
{
    modbus_t *ctx;

    // Create TCP connection
    ctx = modbus_new_tcp("127.0.0.1", 502);
    if (ctx == NULL)
    {
        fprintf(stderr, "Failed to create modbus context\n");
        return -1;
    }
    printf("Created Modbus context\n");

    // Set a 1 second timeout
    modbus_set_response_timeout(ctx, 1, 0);

    // Connect
    if (modbus_connect(ctx) == -1)
    {
        fprintf(stderr, "Connection failed: %s\n", modbus_strerror(errno));
        modbus_free(ctx);
        return -1;
    }
    printf("Connected to server\n");

    // Run tests
    test_holding_registers(ctx);
    test_coils(ctx);
    test_input_registers(ctx);

    // Clean up
    modbus_close(ctx);
    modbus_free(ctx);
    printf("\nTest complete\n");

    return 0;
}