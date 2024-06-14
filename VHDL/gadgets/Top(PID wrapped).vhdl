LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ARCHITECTURE bhvr OF CustomWrapper IS
BEGIN
    DUT : ENTITY WORK.PID_wrapped PORT MAP(
        actual => InputA,
        setpoint => x"0000",
        control => OutputA,

        K_P => Control1(31 DOWNTO 0),
        K_I => Control2(31 DOWNTO 0),
        K_D => Control3(31 DOWNTO 0),

        threshold_I => x"0000" & Control4(31 DOWNTO 16) & x"00000000",
        wrapped_I => (15 DOWNTO 0) & Control4(15 DOWNTO 0) & x"00000000",

        holding_time => Control5(31 DOWNTO 0),

        limit_sum => Control6(31 DOWNTO 16),

        Reset => Control0(0),

        Clk => Clk
    );
END bhvr;