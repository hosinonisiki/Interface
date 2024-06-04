LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL rin_setpoint : signed(15 DOWNTO 0);
BEGIN
    DUT : ENTITY WORK.PID(nodecay) PORT MAP(
        actual => InputA,
        setpoint => rin_setpoint,
        control => OutputA,

        K_P => signed(Control1(31 DOWNTO 0)),
        K_I => signed(Control2(31 DOWNTO 0)),
        K_D => signed(Control3(31 DOWNTO 0)),

        limit_I => x"0001000000000000",

        limit_sum => x"7FFF",

        decay_I => x"40000000",

        Reset => Control0(0),

        Clk => Clk
    );

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Control0(0) = '1' THEN
                rin_setpoint <= InputA;
            END IF;
        END IF;
    END PROCESS;
END bhvr;