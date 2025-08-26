PROGRAM prog0
  VAR
    test_output AT %QX0.0 : BOOL;
    test_counter AT %MW0 : INT;
  END_VAR

  test_output := TRUE;
  test_counter := test_counter + 1;
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK Main(INTERVAL := T#100ms,PRIORITY := 0);
    PROGRAM Inst0 WITH Main : prog0;
  END_RESOURCE
END_CONFIGURATION