LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY CDC IS
    PORT(
        Clk : IN std_logic;
        rate : IN unsigned(3 DOWNTO 0);
        MyClk : OUT std_logic
    );
END CDC;

ARCHITECTURE bhvr OF CDC IS
    SIGNAL counter : unsigned(3 DOWNTO 0) := x"0";
    SIGNAL output : std_logic := '0';
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF rate = x"1" OR rate = x"0" THEN
                output <= '0';
            ELSE
                IF counter = rate - x"1" THEN
                    counter <= x"0";
                    output <= '1';
                ELSE
                    output <= '0';
                    counter <= counter + x"1";
                END IF;
            END IF;
        END IF;
    END PROCESS;
    MyClk <= Clk WHEN rate = x"1" ELSE
              output;
END bhvr;