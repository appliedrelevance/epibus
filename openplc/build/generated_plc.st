PROGRAM Actuators
  VAR
    PON00 AT %IX0.0 : BOOL;
    PON01 AT %IX0.1 : BOOL;
    PON02 AT %IX0.2 : BOOL;
    PON03 AT %IX0.3 : BOOL;
    PON04 AT %IX0.4 : BOOL;
    PON05 AT %IX0.5 : BOOL;
    PON06 AT %IX0.6 : BOOL;
    PON07 AT %IX0.7 : BOOL;
    POF00 AT %IX1.0 : BOOL;
    POF01 AT %IX1.1 : BOOL;
    POF02 AT %IX1.2 : BOOL;
    POF03 AT %IX1.3 : BOOL;
    POF04 AT %IX1.4 : BOOL;
    POF05 AT %IX1.5 : BOOL;
    POF06 AT %IX1.6 : BOOL;
    POF07 AT %IX1.7 : BOOL;
    LED00 AT %QX0.0 : BOOL;
    LED01 AT %QX0.1 : BOOL;
    LED02 AT %QX0.2 : BOOL;
    LED03 AT %QX0.3 : BOOL;
    LED04 AT %QX0.4 : BOOL;
    LED05 AT %QX0.5 : BOOL;
    LED06 AT %QX0.6 : BOOL;
    LED07 AT %QX0.7 : BOOL;
  END_VAR

  LED00 := NOT(POF00) AND (LED00 OR PON00);
  LED01 := NOT(POF01) AND (LED01 OR PON01);
  LED02 := NOT(POF02) AND (LED02 OR PON02);
  LED03 := NOT(POF03) AND (LED03 OR PON03);
  LED04 := NOT(POF04) AND (LED04 OR PON04);
  LED05 := NOT(POF05) AND (LED05 OR PON05);
  LED06 := NOT(POF06) AND (LED06 OR PON06);
  LED07 := NOT(POF07) AND (LED07 OR PON07);
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : Actuators;
  END_RESOURCE
END_CONFIGURATION
