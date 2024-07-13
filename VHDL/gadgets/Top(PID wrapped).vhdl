LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL output_1 : signed(15 DOWNTO 0);
    SIGNAL output_2 : signed(15 DOWNTO 0);
    SIGNAL debug_1 : signed(15 DOWNTO 0);
    SIGNAL debug_2 : signed(15 DOWNTO 0);
BEGIN
    DUT1 : ENTITY WORK.PID_wrapped(hold_I) PORT MAP(
        actual => InputA,
        setpoint => signed(Control6(15 DOWNTO 0)),
        control => output_1,

        K_P => signed(Control1(31 DOWNTO 0)),
        K_I => signed(Control2(31 DOWNTO 0)),
        K_D => signed(Control3(31 DOWNTO 0)),

        threshold_I => (15 DOWNTO 0 => Control4(31)) & signed(Control4(31 DOWNTO 16)) & x"00000000",
        wrapped_I => (15 DOWNTO 0 => Control4(15)) & signed(Control4(15 DOWNTO 0)) & x"00000000",

        holding_time => unsigned(Control5(31 DOWNTO 0)),

        limit_sum => signed(Control6(31 DOWNTO 16)),

        debug_sel => Control8(31 DOWNTO 28),
        debug => debug_1,

        Reset => Control0(0),

        Clk => Clk
    );

    DUT2 : ENTITY WORK.PID_wrapped(hold_setpoint) PORT MAP(
        actual => InputA,
        setpoint => signed(Control6(15 DOWNTO 0)),
        control => output_2,

        K_P => signed(Control1(31 DOWNTO 0)),
        K_I => signed(Control2(31 DOWNTO 0)),
        K_D => signed(Control3(31 DOWNTO 0)),

        threshold_I => (15 DOWNTO 0 => Control4(31)) & signed(Control4(31 DOWNTO 16)) & x"00000000",
        wrapped_I => (15 DOWNTO 0 => Control4(15)) & signed(Control4(15 DOWNTO 0)) & x"00000000",

        holding_time => unsigned(Control5(31 DOWNTO 0)),

        limit_sum => signed(Control6(31 DOWNTO 16)),

        debug_sel => Control8(31 DOWNTO 28),
        debug => debug_2,

        Reset => Control0(0),

        Clk => Clk
    );

    OutputA <= output_1 WHEN Control0(1) = '0' ELSE output_2;
    OutputB <= output_1 WHEN Control0(1) = '0' ELSE output_2;
    OutputC <= debug_1 WHEN Control0(1) = '0' ELSE debug_2;
END bhvr;