(* =============================================== *)
(*  OpenPLC Intralogistics Learning Lab Project  *)
(*  Converted from CODESYS Version               *)
(*  Compatible with OpenPLC Editor v3.0+         *)
(* =============================================== *)

PROGRAM Main
VAR
    (* ===================== *)
    (* System Control Variables *)
    (* ===================== *)
    System_Initialize       : BOOL := TRUE;     // System initialization flag
    System_Enable           : BOOL := FALSE;    // System enable
    System_Reset            : BOOL := FALSE;    // System reset
    Manual_Mode_Request     : BOOL := FALSE;    // Manual mode request
    
    (* ===================== *)
    (* Robot Control Variables *)
    (* ===================== *)
    Robot_Current_State     : INT := 0;         // Robot state (0=IDLE, 1=MOVING_TO_BIN, etc.)
    Robot_Target_Bin        : INT := 0;         // Target bin number (1-12)
    Robot_Target_Station    : INT := 0;         // Target station (0=NONE, 1=RECEIVING, 2=ASSEMBLY, 3=WAREHOUSE)
    Robot_Position_X        : INT := 0;         // Robot X position
    Robot_Position_Y        : INT := 0;         // Robot Y position  
    Robot_Position_Z        : INT := 0;         // Robot Z position
    Robot_Ready             : BOOL := FALSE;    // Robot ready for operation
    Robot_Busy              : BOOL := FALSE;    // Robot busy
    Robot_Error             : BOOL := FALSE;    // Robot error
    Robot_At_Home           : BOOL := FALSE;    // Robot at home position
    Robot_Operation_Complete: BOOL := FALSE;    // Robot operation complete
    
    (* ===================== *)
    (* Robot Operation Timers *)
    (* ===================== *)
    Robot_Move_Timer        : TON;              // Movement timer
    Robot_Pick_Timer        : TON;              // Pick operation timer
    Robot_Place_Timer       : TON;              // Place operation timer
    Robot_Complete_Timer    : TON;              // Operation complete timer
    Robot_Operation_Step    : INT := 0;         // Operation step counter
    
    (* ===================== *)
    (* Conveyor Control Variables *)
    (* ===================== *)
    Conveyor1_Status        : INT := 0;         // Conveyor status (0=STOPPED, 1=RUNNING, 2=FAULT)
    Conveyor2_Status        : INT := 0;
    Conveyor3_Status        : INT := 0;
    Conveyor4_Status        : INT := 0;
    Conveyor1_Speed         : INT := 100;       // Conveyor speed in mm/min
    Conveyor2_Speed         : INT := 100;
    Conveyor3_Speed         : INT := 100;
    Conveyor4_Speed         : INT := 100;
    Conveyors_System_OK     : BOOL := TRUE;     // Conveyor system OK
    Conveyors_Any_Fault     : BOOL := FALSE;    // Any conveyor fault
    
    (* ===================== *)
    (* Safety System Variables *)
    (* ===================== *)
    Safety_OK               : BOOL := FALSE;    // Safety system OK
    Emergency_Stop_Active   : BOOL := FALSE;    // Emergency stop active
    Safety_Gate_OK          : BOOL := TRUE;     // Safety gate OK (simulated)
    Light_Curtain_OK        : BOOL := TRUE;     // Light curtain OK (simulated)
    
    (* ===================== *)
    (* RFID System Variables *)
    (* ===================== *)
    RFID_Reader1_Status     : INT := 0;         // RFID reader status (0=IDLE, 1=READING, 2=VALID, 3=ERROR)
    RFID_Reader2_Status     : INT := 0;
    RFID_Reader1_Tag_ID     : DINT := 0;        // 32-bit tag ID
    RFID_Reader2_Tag_ID     : DINT := 0;
    RFID_System_OK          : BOOL := TRUE;     // RFID system OK
    RFID_Any_Error          : BOOL := FALSE;    // Any RFID error
    
    (* ===================== *)
    (* Pick Operation Control *)
    (* ===================== *)
    Pick_Active             : BOOL := FALSE;    // Pick operation active
    Pick_Request_Detected   : BOOL := FALSE;    // Pick request detected
    Pick_Operation_Timer    : TON;              // Pick operation timer
    Pick_Complete_Timer     : TON;              // Pick complete timer
    
    (* Edge detection for pick requests *)
    Pick_Bin_01_Edge        : BOOL := FALSE;
    Pick_Bin_02_Edge        : BOOL := FALSE;
    Pick_Bin_03_Edge        : BOOL := FALSE;
    Pick_Bin_04_Edge        : BOOL := FALSE;
    Pick_Bin_05_Edge        : BOOL := FALSE;
    Pick_Bin_06_Edge        : BOOL := FALSE;
    Pick_Bin_07_Edge        : BOOL := FALSE;
    Pick_Bin_08_Edge        : BOOL := FALSE;
    Pick_Bin_09_Edge        : BOOL := FALSE;
    Pick_Bin_10_Edge        : BOOL := FALSE;
    Pick_Bin_11_Edge        : BOOL := FALSE;
    Pick_Bin_12_Edge        : BOOL := FALSE;
    
    Pick_Bin_01_Last        : BOOL := FALSE;
    Pick_Bin_02_Last        : BOOL := FALSE;
    Pick_Bin_03_Last        : BOOL := FALSE;
    Pick_Bin_04_Last        : BOOL := FALSE;
    Pick_Bin_05_Last        : BOOL := FALSE;
    Pick_Bin_06_Last        : BOOL := FALSE;
    Pick_Bin_07_Last        : BOOL := FALSE;
    Pick_Bin_08_Last        : BOOL := FALSE;
    Pick_Bin_09_Last        : BOOL := FALSE;
    Pick_Bin_10_Last        : BOOL := FALSE;
    Pick_Bin_11_Last        : BOOL := FALSE;
    Pick_Bin_12_Last        : BOOL := FALSE;
    
    (* ===================== *)
    (* System Status Variables *)
    (* ===================== *)
    System_Ready            : BOOL := FALSE;    // System ready for operation
    All_Systems_OK          : BOOL := FALSE;    // All systems OK
    Any_System_Error        : BOOL := FALSE;    // Any system error
    
    (* ===================== *)
    (* Timing Variables *)
    (* ===================== *)
    Cycle_Counter           : DINT := 0;        // Main cycle counter
    Uptime_Counter          : INT := 0;         // Uptime counter
    Heartbeat_Counter       : INT := 0;         // Heartbeat counter
    Heartbeat_Timer         : BOOL := FALSE;    // Heartbeat timer toggle
    
    (* ===================== *)
    (* Initialization Timer *)
    (* ===================== *)
    Init_Timer              : TON;              // Initialization timer
    Init_Complete           : BOOL := FALSE;    // Initialization complete
    
    (* ===================== *)
    (* Beacon Control Variables *)
    (* ===================== *)
    Beacon_Flash_Timer      : TON;              // Beacon flash timer
    Beacon_Flash_State      : BOOL := FALSE;    // Beacon flash state
END_VAR

(* =============================================== *)
(*              SYSTEM INITIALIZATION             *)
(* =============================================== *)

IF System_Initialize AND NOT Init_Complete THEN
    Init_Timer(IN := TRUE, PT := T#2s);
    
    (* Reset all MODBUS registers during initialization *)
    %MW100 := 0;        (* Cycle_Counter *)
    %MW101 := 0;        (* Pick_Operations_Total *)
    %MW102 := 0;        (* Assembly_Picks *)
    %MW103 := 0;        (* Receiving_Picks *)
    %MW104 := 0;        (* Warehouse_Picks *)
    %MW105 := 0;        (* Error_Count *)
    %MW106 := 0;        (* Uptime_Seconds *)
    %MW107 := 0;        (* System_Status - Stopped *)
    %MW108 := 0;        (* Current_Bin_Selection *)
    %MW109 := 0;        (* Robot_Position_X *)
    %MW110 := 0;        (* Robot_Position_Y *)
    %MW111 := 0;        (* Robot_Position_Z *)
    
    (* Initialize RFID registers *)
    %MW200 := 0;        (* RFID_Reader1_Tag_ID_Low *)
    %MW201 := 0;        (* RFID_Reader1_Tag_ID_High *)
    %MW202 := 0;        (* RFID_Reader2_Tag_ID_Low *)
    %MW203 := 0;        (* RFID_Reader2_Tag_ID_High *)
    %MW204 := 0;        (* RFID_Reader1_Status *)
    %MW205 := 0;        (* RFID_Reader2_Status *)
    
    (* Initialize Conveyor registers *)
    %MW300 := 0;        (* Conveyor1_Status *)
    %MW301 := 0;        (* Conveyor2_Status *)
    %MW302 := 0;        (* Conveyor3_Status *)
    %MW303 := 0;        (* Conveyor4_Status *)
    %MW304 := 100;      (* Conveyor1_Speed *)
    %MW305 := 100;      (* Conveyor2_Speed *)
    %MW306 := 100;      (* Conveyor3_Speed *)
    %MW307 := 100;      (* Conveyor4_Speed *)
    
    (* Initialize robot state *)
    Robot_Current_State := 0;       (* ROBOT_IDLE *)
    Robot_Target_Bin := 0;
    Robot_Target_Station := 0;      (* STATION_NONE *)
    Robot_Position_X := 0;
    Robot_Position_Y := 0;
    Robot_Position_Z := 0;
    
    IF Init_Timer.Q THEN
        Init_Complete := TRUE;
        System_Initialize := FALSE;
        Init_Timer(IN := FALSE);
    END_IF
END_IF

(* Only run main program after initialization *)
IF NOT Init_Complete THEN
    RETURN;
END_IF

(* =============================================== *)
(*                INPUT PROCESSING                *)
(* =============================================== *)

(* Read physical inputs *)
Emergency_Stop_Active := NOT %IX0.0;       (* Emergency stop (normally closed) *)
System_Reset := %IX0.1;                    (* Manual reset button *)

(* System enable logic *)
IF %IX0.2 AND NOT System_Enable THEN       (* Start button *)
    System_Enable := TRUE;
ELSIF %IX0.3 OR Emergency_Stop_Active THEN (* Stop button or E-Stop *)
    System_Enable := FALSE;
END_IF

(* =============================================== *)
(*              SAFETY SYSTEM LOGIC               *)
(* =============================================== *)

(* Safety system evaluation *)
Safety_OK := NOT Emergency_Stop_Active AND 
             Safety_Gate_OK AND 
             Light_Curtain_OK;

(* Emergency shutdown logic *)
IF NOT Safety_OK THEN
    System_Enable := FALSE;
    %MW107 := 4;                (* System_Status = Error *)
    
    (* Reset all operation flags *)
    %QX125.1 := FALSE;          (* PLC_Cycle_Running *)
    %QX125.0 := TRUE;           (* PLC_Cycle_Stopped *)
    
    (* Disable all outputs *)
    %QX1.0 := FALSE;            (* Conveyor1_Motor *)
    %QX1.1 := FALSE;            (* Conveyor2_Motor *)
    %QX1.2 := FALSE;            (* Conveyor3_Motor *)
    %QX1.3 := FALSE;            (* Conveyor4_Motor *)
    %QX2.0 := FALSE;            (* Robot_Enable *)
    
ELSE
    (* Safety OK - proceed with normal operation *)
    
    (* =============================================== *)
    (*           PICK OPERATION DETECTION             *)
    (* =============================================== *)
    
    (* Edge detection for bin selection *)
    Pick_Bin_01_Edge := %QX250.0 AND NOT Pick_Bin_01_Last;
    Pick_Bin_02_Edge := %QX250.1 AND NOT Pick_Bin_02_Last;
    Pick_Bin_03_Edge := %QX250.2 AND NOT Pick_Bin_03_Last;
    Pick_Bin_04_Edge := %QX250.3 AND NOT Pick_Bin_04_Last;
    Pick_Bin_05_Edge := %QX250.4 AND NOT Pick_Bin_05_Last;
    Pick_Bin_06_Edge := %QX250.5 AND NOT Pick_Bin_06_Last;
    Pick_Bin_07_Edge := %QX250.6 AND NOT Pick_Bin_07_Last;
    Pick_Bin_08_Edge := %QX250.7 AND NOT Pick_Bin_08_Last;
    Pick_Bin_09_Edge := %QX251.0 AND NOT Pick_Bin_09_Last;
    Pick_Bin_10_Edge := %QX251.1 AND NOT Pick_Bin_10_Last;
    Pick_Bin_11_Edge := %QX251.2 AND NOT Pick_Bin_11_Last;
    Pick_Bin_12_Edge := %QX251.3 AND NOT Pick_Bin_12_Last;
    
    (* Store previous states *)
    Pick_Bin_01_Last := %QX250.0;
    Pick_Bin_02_Last := %QX250.1;
    Pick_Bin_03_Last := %QX250.2;
    Pick_Bin_04_Last := %QX250.3;
    Pick_Bin_05_Last := %QX250.4;
    Pick_Bin_06_Last := %QX250.5;
    Pick_Bin_07_Last := %QX250.6;
    Pick_Bin_08_Last := %QX250.7;
    Pick_Bin_09_Last := %QX251.0;
    Pick_Bin_10_Last := %QX251.1;
    Pick_Bin_11_Last := %QX251.2;
    Pick_Bin_12_Last := %QX251.3;
    
    (* Determine which bin was selected *)
    Pick_Request_Detected := Pick_Bin_01_Edge OR Pick_Bin_02_Edge OR Pick_Bin_03_Edge OR Pick_Bin_04_Edge OR
                            Pick_Bin_05_Edge OR Pick_Bin_06_Edge OR Pick_Bin_07_Edge OR Pick_Bin_08_Edge OR
                            Pick_Bin_09_Edge OR Pick_Bin_10_Edge OR Pick_Bin_11_Edge OR Pick_Bin_12_Edge;
    
    IF Pick_Request_Detected AND NOT Pick_Active THEN
        (* Determine target bin *)
        IF Pick_Bin_01_Edge THEN Robot_Target_Bin := 1;
        ELSIF Pick_Bin_02_Edge THEN Robot_Target_Bin := 2;
        ELSIF Pick_Bin_03_Edge THEN Robot_Target_Bin := 3;
        ELSIF Pick_Bin_04_Edge THEN Robot_Target_Bin := 4;
        ELSIF Pick_Bin_05_Edge THEN Robot_Target_Bin := 5;
        ELSIF Pick_Bin_06_Edge THEN Robot_Target_Bin := 6;
        ELSIF Pick_Bin_07_Edge THEN Robot_Target_Bin := 7;
        ELSIF Pick_Bin_08_Edge THEN Robot_Target_Bin := 8;
        ELSIF Pick_Bin_09_Edge THEN Robot_Target_Bin := 9;
        ELSIF Pick_Bin_10_Edge THEN Robot_Target_Bin := 10;
        ELSIF Pick_Bin_11_Edge THEN Robot_Target_Bin := 11;
        ELSIF Pick_Bin_12_Edge THEN Robot_Target_Bin := 12;
        END_IF
        
        (* Determine target station *)
        IF %QX252.4 THEN                    (* To_Receiving_Sta_1 *)
            Robot_Target_Station := 1;      (* STATION_RECEIVING *)
        ELSIF %QX252.6 THEN                 (* To_Assembly_Sta_2 *)
            Robot_Target_Station := 2;      (* STATION_ASSEMBLY *)
        ELSE
            Robot_Target_Station := 3;      (* STATION_WAREHOUSE *)
        END_IF
        
        (* Update MODBUS register *)
        %MW108 := Robot_Target_Bin;         (* Current_Bin_Selection *)
        
        (* Start pick operation *)
        Pick_Active := TRUE;
        Pick_Operation_Timer(IN := TRUE, PT := T#30s);  (* 30 second timeout *)
    END_IF
    
    (* =============================================== *)
    (*              ROBOT CONTROL LOGIC               *)
    (* =============================================== *)
    
    (* Read robot feedback *)
    Robot_At_Home := %IX2.0;               (* Robot_Home_Position *)
    
    (* Robot state machine *)
    CASE Robot_Current_State OF
        
        0: (* ROBOT_IDLE *)
            Robot_Ready := System_Enable AND Robot_At_Home AND NOT Robot_Error;
            Robot_Busy := FALSE;
            Robot_Operation_Complete := FALSE;
            
            (* Robot enable control *)
            %QX2.0 := System_Enable;        (* Robot_Enable *)
            
            (* Start operation on pick request *)
            IF Pick_Active AND Robot_Ready AND Robot_Target_Bin > 0 THEN
                Robot_Current_State := 1;   (* ROBOT_MOVING_TO_BIN *)
                Robot_Operation_Step := 1;
                Robot_Move_Timer(IN := FALSE);
            END_IF
        
        1: (* ROBOT_MOVING_TO_BIN *)
            Robot_Ready := FALSE;
            Robot_Busy := TRUE;
            
            (* Send move command *)
            %QX2.1 := TRUE;                 (* Robot_Move_To_Bin *)
            
            (* Calculate bin position (3x4 grid layout) *)
            IF Robot_Target_Bin >= 1 AND Robot_Target_Bin <= 12 THEN
                Robot_Position_X := ((Robot_Target_Bin - 1) MOD 4) * 100 + 100;
                Robot_Position_Y := ((Robot_Target_Bin - 1) / 4) * 100 + 100;
                Robot_Position_Z := 50;     (* Picking height *)
            END_IF
            
            (* Timer for movement (5 seconds) *)
            Robot_Move_Timer(IN := TRUE, PT := T#5s);
            IF Robot_Move_Timer.Q THEN
                Robot_Move_Timer(IN := FALSE);
                Robot_Current_State := 2;   (* ROBOT_AT_BIN *)
                %QX2.1 := FALSE;           (* Robot_Move_To_Bin *)
            END_IF
        
        2: (* ROBOT_AT_BIN *)
            Robot_Busy := TRUE;
            Robot_Current_State := 3;       (* ROBOT_PICKING *)
        
        3: (* ROBOT_PICKING *)
            Robot_Busy := TRUE;
            
            (* Close gripper to pick item *)
            %QX2.5 := TRUE;                 (* Robot_Gripper_Close_Cmd *)
            %QX2.4 := FALSE;                (* Robot_Gripper_Open_Cmd *)
            
            (* Pick timer (3 seconds) *)
            Robot_Pick_Timer(IN := TRUE, PT := T#3s);
            IF Robot_Pick_Timer.Q THEN
                Robot_Pick_Timer(IN := FALSE);
                Robot_Current_State := 4;   (* ROBOT_MOVING_TO_STATION *)
                %QX2.5 := FALSE;           (* Robot_Gripper_Close_Cmd *)
            END_IF
        
        4: (* ROBOT_MOVING_TO_STATION *)
            Robot_Busy := TRUE;
            
            (* Send move command *)
            %QX2.2 := TRUE;                 (* Robot_Move_To_Station *)
            
            (* Calculate station position *)
            CASE Robot_Target_Station OF
                1: (* STATION_RECEIVING *)
                    Robot_Position_X := 500;
                    Robot_Position_Y := 100;
                2: (* STATION_ASSEMBLY *)
                    Robot_Position_X := 500;
                    Robot_Position_Y := 200;
                3: (* STATION_WAREHOUSE *)
                    Robot_Position_X := 500;
                    Robot_Position_Y := 300;
                ELSE
                    Robot_Position_X := 0;
                    Robot_Position_Y := 0;
            END_CASE
            Robot_Position_Z := 50;         (* Placing height *)
            
            (* Timer for movement (5 seconds) *)
            Robot_Move_Timer(IN := TRUE, PT := T#5s);
            IF Robot_Move_Timer.Q THEN
                Robot_Move_Timer(IN := FALSE);
                Robot_Current_State := 5;   (* ROBOT_AT_STATION *)
                %QX2.2 := FALSE;           (* Robot_Move_To_Station *)
            END_IF
        
        5: (* ROBOT_AT_STATION *)
            Robot_Busy := TRUE;
            Robot_Current_State := 6;       (* ROBOT_PLACING *)
        
        6: (* ROBOT_PLACING *)
            Robot_Busy := TRUE;
            
            (* Open gripper to place item *)
            %QX2.4 := TRUE;                 (* Robot_Gripper_Open_Cmd *)
            %QX2.5 := FALSE;                (* Robot_Gripper_Close_Cmd *)
            
            (* Place timer (3 seconds) *)
            Robot_Place_Timer(IN := TRUE, PT := T#3s);
            IF Robot_Place_Timer.Q THEN
                Robot_Place_Timer(IN := FALSE);
                Robot_Current_State := 7;   (* ROBOT_RETURNING_HOME *)
                %QX2.4 := FALSE;           (* Robot_Gripper_Open_Cmd *)
            END_IF
        
        7: (* ROBOT_RETURNING_HOME *)
            Robot_Busy := TRUE;
            
            (* Send move home command *)
            %QX2.3 := TRUE;                 (* Robot_Move_Home *)
            
            (* Reset position registers *)
            Robot_Position_X := 0;
            Robot_Position_Y := 0;
            Robot_Position_Z := 0;
            
            (* Timer for movement (5 seconds) *)
            Robot_Move_Timer(IN := TRUE, PT := T#5s);
            IF Robot_Move_Timer.Q THEN
                Robot_Move_Timer(IN := FALSE);
                Robot_Operation_Complete := TRUE;
                Robot_Current_State := 0;   (* ROBOT_IDLE *)
                %QX2.3 := FALSE;           (* Robot_Move_Home *)
                
                (* Update statistics *)
                %MW101 := %MW101 + 1;       (* Pick_Operations_Total *)
                CASE Robot_Target_Station OF
                    1: %MW103 := %MW103 + 1; (* Receiving_Picks *)
                    2: %MW102 := %MW102 + 1; (* Assembly_Picks *)
                    3: %MW104 := %MW104 + 1; (* Warehouse_Picks *)
                END_CASE
                
                (* Set completion flags *)
                CASE Robot_Target_Station OF
                    1: %QX125.6 := TRUE;    (* Pick_To_Receiving_Complete *)
                    2: %QX125.4 := TRUE;    (* Pick_To_Assembly_Complete *)
                    3: %QX126.0 := TRUE;    (* Pick_To_Warehouse_Complete *)
                END_CASE
                
                (* Start complete signal timer (10 seconds) *)
                Robot_Complete_Timer(IN := TRUE, PT := T#10s);
                
                (* End pick operation *)
                Pick_Active := FALSE;
                Pick_Operation_Timer(IN := FALSE);
            END_IF
        
        8: (* ROBOT_ERROR *)
            Robot_Ready := FALSE;
            Robot_Busy := FALSE;
            Robot_Error := TRUE;
            
            (* Stop all robot commands *)
            %QX2.0 := FALSE;                (* Robot_Enable *)
            %QX2.1 := FALSE;                (* Robot_Move_To_Bin *)
            %QX2.2 := FALSE;                (* Robot_Move_To_Station *)
            %QX2.3 := FALSE;                (* Robot_Move_Home *)
            %QX2.4 := FALSE;                (* Robot_Gripper_Open_Cmd *)
            %QX2.5 := FALSE;                (* Robot_Gripper_Close_Cmd *)
            
            (* Reset to idle on reset command *)
            IF System_Reset THEN
                Robot_Current_State := 0;   (* ROBOT_IDLE *)
                Robot_Error := FALSE;
                %QX2.6 := TRUE;             (* Robot_Reset *)
            ELSE
                %QX2.6 := FALSE;           (* Robot_Reset *)
            END_IF
    
    END_CASE
    
    (* Complete signal pulse control *)
    Robot_Complete_Timer(IN := Robot_Operation_Complete OR %QX125.4 OR %QX125.6 OR %QX126.0);
    IF Robot_Complete_Timer.Q THEN
        Robot_Operation_Complete := FALSE;
        %QX125.4 := FALSE;              (* Pick_To_Assembly_Complete *)
        %QX125.6 := FALSE;              (* Pick_To_Receiving_Complete *)
        %QX126.0 := FALSE;              (* Pick_To_Warehouse_Complete *)
        Robot_Complete_Timer(IN := FALSE);
    END_IF
    
    (* Error detection *)
    IF %IX2.5 THEN                      (* Robot_Error_Status *)
        Robot_Current_State := 8;       (* ROBOT_ERROR *)
    END_IF
    
    (* =============================================== *)
    (*             CONVEYOR CONTROL LOGIC             *)
    (* =============================================== *)
    
    (* Simple conveyor control logic *)
    IF System_Enable THEN
        (* Start conveyors when system is running *)
        %QX1.0 := TRUE;                 (* Conveyor1_Motor *)
        %QX1.1 := TRUE;                 (* Conveyor2_Motor *)
        %QX1.2 := TRUE;                 (* Conveyor3_Motor *)
        %QX1.3 := TRUE;                 (* Conveyor4_Motor *)
        
        Conveyor1_Status := 1;          (* RUNNING *)
        Conveyor2_Status := 1;
        Conveyor3_Status := 1;
        Conveyor4_Status := 1;
    ELSE
        (* Stop conveyors when system is disabled *)
        %QX1.0 := FALSE;                (* Conveyor1_Motor *)
        %QX1.1 := FALSE;                (* Conveyor2_Motor *)
        %QX1.2 := FALSE;                (* Conveyor3_Motor *)
        %QX1.3 := FALSE;                (* Conveyor4_Motor *)
        
        Conveyor1_Status := 0;          (* STOPPED *)
        Conveyor2_Status := 0;
        Conveyor3_Status := 0;
        Conveyor4_Status := 0;
    END_IF
    
    (* Update conveyor status registers *)
    %MW300 := Conveyor1_Status;
    %MW301 := Conveyor2_Status;
    %MW302 := Conveyor3_Status;
    %MW303 := Conveyor4_Status;
    %MW304 := Conveyor1_Speed;
    %MW305 := Conveyor2_Speed;
    %MW306 := Conveyor3_Speed;
    %MW307 := Conveyor4_Speed;
    
    (* =============================================== *)
    (*              RFID SYSTEM LOGIC                 *)
    (* =============================================== *)
    
    (* Simple RFID reader control *)
    IF System_Enable THEN
        %QX4.0 := TRUE;                 (* RFID_Reader1_Enable *)
        %QX4.1 := TRUE;                 (* RFID_Reader2_Enable *)
        
        (* Simulate tag reading when present *)
        IF %IX3.2 THEN                  (* RFID_Reader1_Tag_Present *)
            RFID_Reader1_Status := 2;   (* VALID *)
            RFID_Reader1_Tag_ID := 12345678; (* Example tag ID *)
            %QX4.2 := TRUE;             (* RFID_Reader1_Read *)
        ELSE
            RFID_Reader1_Status := 0;   (* IDLE *)
            RFID_Reader1_Tag_ID := 0;
            %QX4.2 := FALSE;            (* RFID_Reader1_Read *)
        END_IF
        
        IF %IX3.3 THEN                  (* RFID_Reader2_Tag_Present *)
            RFID_Reader2_Status := 2;   (* VALID *)
            RFID_Reader2_Tag_ID := 87654321; (* Example tag ID *)
            %QX4.3 := TRUE;             (* RFID_Reader2_Read *)
        ELSE
            RFID_Reader2_Status := 0;   (* IDLE *)
            RFID_Reader2_Tag_ID := 0;
            %QX4.3 := FALSE;            (* RFID_Reader2_Read *)
        END_IF
    ELSE
        %QX4.0 := FALSE;                (* RFID_Reader1_Enable *)
        %QX4.1 := FALSE;                (* RFID_Reader2_Enable *)
        %QX4.2 := FALSE;                (* RFID_Reader1_Read *)
        %QX4.3 := FALSE;                (* RFID_Reader2_Read *)
        RFID_Reader1_Status := 0;
        RFID_Reader2_Status := 0;
    END_IF
    
    (* Update RFID status registers *)
    %MW204 := RFID_Reader1_Status;
    %MW205 := RFID_Reader2_Status;
    
    (* Split 32-bit tag IDs into 16-bit registers *)
    %MW200 := RFID_Reader1_Tag_ID AND 16#FFFF;          (* Low word *)
    %MW201 := (RFID_Reader1_Tag_ID SHR 16) AND 16#FFFF; (* High word *)
    %MW202 := RFID_Reader2_Tag_ID AND 16#FFFF;          (* Low word *)
    %MW203 := (RFID_Reader2_Tag_ID SHR 16) AND 16#FFFF; (* High word *)
    
    (* =============================================== *)
    (*                 SYSTEM STATUS                   *)
    (* =============================================== *)
    
    (* Update system status *)
    IF System_Enable THEN
        IF Pick_Active THEN
            %MW107 := 2;                (* System_Status = Running *)
            %QX125.1 := TRUE;           (* PLC_Cycle_Running *)
            %QX125.0 := FALSE;          (* PLC_Cycle_Stopped *)
        ELSE
            %MW107 := 1;                (* System_Status = Ready *)
            %QX125.1 := FALSE;          (* PLC_Cycle_Running *)
            %QX125.0 := FALSE;          (* PLC_Cycle_Stopped *)
        END_IF
    ELSE
        %MW107 := 0;                    (* System_Status = Stopped *)
        %QX125.1 := FALSE;              (* PLC_Cycle_Running *)
        %QX125.0 := TRUE;               (* PLC_Cycle_Stopped *)
    END_IF
    
END_IF

(* =============================================== *)
(*               BEACON CONTROL LOGIC             *)
(* =============================================== *)

(* Beacon flash timer (1 second period) *)
Beacon_Flash_Timer(IN := TRUE, PT := T#500ms);
IF Beacon_Flash_Timer.Q THEN
    Beacon_Flash_State := NOT Beacon_Flash_State;
    Beacon_Flash_Timer(IN := FALSE);
END_IF

(* Beacon control logic *)
IF NOT Safety_OK THEN
    (* Red flashing - Emergency/Safety fault *)
    %QX3.2 := Beacon_Flash_State;       (* Red_Beacon *)
    %QX3.1 := FALSE;                    (* Yellow_Beacon *)
    %QX3.0 := FALSE;                    (* Green_Beacon *)
    %QX3.3 := Beacon_Flash_State;       (* Buzzer *)
ELSIF Any_System_Error THEN
    (* Yellow flashing - System error *)
    %QX3.2 := FALSE;                    (* Red_Beacon *)
    %QX3.1 := Beacon_Flash_State;       (* Yellow_Beacon *)
    %QX3.0 := FALSE;                    (* Green_Beacon *)
    %QX3.3 := FALSE;                    (* Buzzer *)
ELSIF Manual_Mode_Request THEN
    (* Yellow solid - Manual mode *)
    %QX3.2 := FALSE;                    (* Red_Beacon *)
    %QX3.1 := TRUE;                     (* Yellow_Beacon *)
    %QX3.0 := FALSE;                    (* Green_Beacon *)
    %QX3.3 := FALSE;                    (* Buzzer *)
ELSIF System_Enable AND Pick_Active THEN
    (* Green flashing - Operation active *)
    %QX3.2 := FALSE;                    (* Red_Beacon *)
    %QX3.1 := FALSE;                    (* Yellow_Beacon *)
    %QX3.0 := Beacon_Flash_State;       (* Green_Beacon *)
    %QX3.3 := FALSE;                    (* Buzzer *)
ELSIF System_Enable THEN
    (* Green solid - System ready *)
    %QX3.2 := FALSE;                    (* Red_Beacon *)
    %QX3.1 := FALSE;                    (* Yellow_Beacon *)
    %QX3.0 := TRUE;                     (* Green_Beacon *)
    %QX3.3 := FALSE;                    (* Buzzer *)
ELSE
    (* All off - System stopped *)
    %QX3.2 := FALSE;                    (* Red_Beacon *)
    %QX3.1 := FALSE;                    (* Yellow_Beacon *)
    %QX3.0 := FALSE;                    (* Green_Beacon *)
    %QX3.3 := FALSE;                    (* Buzzer *)
END_IF

(* =============================================== *)
(*              STATUS CALCULATIONS               *)
(* =============================================== *)

System_Ready := Safety_OK AND 
                Conveyors_System_OK AND 
                RFID_System_OK AND 
                NOT Robot_Error;

All_Systems_OK := System_Ready AND System_Enable;

Any_System_Error := Emergency_Stop_Active OR 
                   Conveyors_Any_Fault OR 
                   RFID_Any_Error OR 
                   Robot_Error;

(* Update physical status outputs *)
%QX0.0 := All_Systems_OK;               (* System_Running *)
%QX0.1 := Any_System_Error;             (* System_Error *)
%QX0.2 := Safety_OK;                    (* Safety_OK *)
%QX0.3 := Manual_Mode_Request;          (* Manual_Mode *)

(* =============================================== *)
(*            TIMING AND HOUSEKEEPING             *)
(* =============================================== *)

(* Cycle counter and timing *)
Cycle_Counter := Cycle_Counter + 1;
%MW100 := TO_INT(Cycle_Counter MOD 32767);  (* Cycle_Counter *)

(* Uptime calculation - increment every 10 cycles (approximately 1 second) *)
Uptime_Counter := Uptime_Counter + 1;
IF Uptime_Counter >= 10 THEN
    Uptime_Counter := 0;
    IF System_Enable THEN
        %MW106 := %MW106 + 1;           (* Uptime_Seconds *)
    END_IF
END_IF

(* Heartbeat counter (500ms toggle) *)
Heartbeat_Counter := Heartbeat_Counter + 1;
IF Heartbeat_Counter >= 5 THEN
    Heartbeat_Counter := 0;
    Heartbeat_Timer := NOT Heartbeat_Timer;
END_IF

(* Error counting *)
IF Any_System_Error THEN
    %MW105 := %MW105 + 1;               (* Error_Count *)
END_IF

(* Update MODBUS position registers *)
%MW109 := Robot_Position_X;             (* Robot_Position_X *)
%MW110 := Robot_Position_Y;             (* Robot_Position_Y *)
%MW111 := Robot_Position_Z;             (* Robot_Position_Z *)

(* Reset pick error flag after timeout *)
Pick_Operation_Timer(IN := Pick_Active);
IF Pick_Operation_Timer.Q THEN
    %QX125.2 := TRUE;                   (* Pick_Error *)
    Pick_Active := FALSE;
    Pick_Operation_Timer(IN := FALSE);
    Robot_Current_State := 0;           (* ROBOT_IDLE *)
END_IF

END_PROGRAM