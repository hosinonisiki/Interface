LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ARCHITECTURE bhvr OF CustomWrapper IS
BEGIN
    DUT : ENTITY WORK.channel_encoder PORT MAP(
        sync_period => Control1(31 DOWNTO 16),
        A => InputA,
        B => InputB,
        O => OutputA,
        Reset => Control0(0),
        Clk => Clk
    );
END bhvr;