PROGRAM prog0
  VAR
    (* Digital Inputs - Read Only *)
    PLC_CYCLE_STOPPED AT %IX0.0 : BOOL;
    PLC_CYCLE_RUNNING AT %IX0.1 : BOOL;
    PICK_ERROR AT %IX0.2 : BOOL;
    PICK_TO_ASSEMBLY_IN_PROCESS AT %IX0.3 : BOOL;
    PICK_TO_ASSEMBLY_COMPLETE AT %IX0.4 : BOOL;
    PICK_TO_RECEIVING_IN_PROCESS AT %IX0.5 : BOOL;
    PICK_TO_RECEIVING_COMPLETE AT %IX0.6 : BOOL;
    PICK_TO_WAREHOUSE_IN_PROCESS AT %IX0.7 : BOOL;
    PICK_TO_WAREHOUSE_COMPLETE AT %IX1.0 : BOOL;

    (* Digital Outputs for Bin Selection *)
    PICK_BIN_01 AT %QX1.3 : BOOL;
    PICK_BIN_02 AT %QX1.4 : BOOL;
    PICK_BIN_03 AT %QX1.5 : BOOL;
    PICK_BIN_04 AT %QX1.6 : BOOL;
    PICK_BIN_05 AT %QX1.7 : BOOL;
    PICK_BIN_06 AT %QX2.0 : BOOL;
    PICK_BIN_07 AT %QX2.1 : BOOL;
    PICK_BIN_08 AT %QX2.2 : BOOL;
    PICK_BIN_09 AT %QX2.3 : BOOL;
    PICK_BIN_10 AT %QX2.4 : BOOL;
    PICK_BIN_11 AT %QX2.5 : BOOL;
    PICK_BIN_12 AT %QX2.6 : BOOL;

    (* Station Selection Outputs *)
    TO_RECEIVING_STA_1 AT %QX4.0 : BOOL;
    FROM_RECEIVING AT %QX4.1 : BOOL;
    TO_ASSEMBLY_STA_1 AT %QX4.2 : BOOL;
    FROM_ASSEMBLY AT %QX4.3 : BOOL;

    (* Control Commands *)
    CONTROL_COMMAND AT %MW0 : INT;  (* Keep this as INT for multi-value commands *)
  END_VAR

  (* Simple program that just keeps the PLC running *)
  PLC_CYCLE_RUNNING := TRUE;
  PLC_CYCLE_STOPPED := FALSE;

END_PROGRAM

CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK Main(INTERVAL := T#100ms,PRIORITY := 0);
    PROGRAM Inst0 WITH Main : prog0;
  END_RESOURCE
END_CONFIGURATION
