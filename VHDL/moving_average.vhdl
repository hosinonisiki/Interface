LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY moving_average IS
    GENERIC(
        tap : INTEGER := 256;
        logtap : INTEGER := 8
    );
    PORT(
        input : IN signed(15 DOWNTO 0);
        output : OUT signed(15 DOWNTO 0);
        Clk : IN std_logic;
        Reset : IN std_logic
    );
END moving_average;

ARCHITECTURE bhvr OF moving_average IS
    SIGNAL avg : signed(15 + logtap DOWNTO 0) := (OTHERS => '0');
    TYPE reg_type IS ARRAY(0 TO tap - 1) OF signed(15 DOWNTO 0);
    SIGNAL reg : reg_type := (OTHERS => x"0000");
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                avg <= (OTHERS => '0');
                reg <= (OTHERS => x"0000");
            ELSE
                avg <= avg + ((logtap - 1 DOWNTO 0 => input(15)) & input) -((logtap - 1 DOWNTO 0 => reg(tap - 1)(15)) & reg(tap - 1));
                reg(0) <= input;
                FOR i IN 1 TO tap - 1 LOOP
                    reg(i) <= reg(i - 1);
                END LOOP;
            END IF;
            output <= avg(logtap + 15 DOWNTO logtap);
        END IF;
    END PROCESS;
END bhvr;