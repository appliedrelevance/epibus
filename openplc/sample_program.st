CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK task0(INTERVAL := T#50ms, PRIORITY := 0);
        PROGRAM instance0 WITH task0 : sample_program;
    END_RESOURCE
END_CONFIGURATION

PROGRAM sample_program
    VAR
        LED00 AT %QX0.0: BOOL;
        LED01 AT %QX0.1: BOOL;
        LED02 AT %QX0.2: BOOL;
        LED03 AT %QX0.3: BOOL;
        LED04 AT %QX0.4: BOOL;
        LED05 AT %QX0.5: BOOL;
        LED06 AT %QX0.6: BOOL;
        LED07 AT %QX0.7: BOOL;
    END_VAR
    
    // Program body - must exist even if empty
    BEGIN
        // Empty body - PSM will control the outputs
    END_PROGRAM