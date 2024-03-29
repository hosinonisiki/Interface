LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY phase2freq IS
    GENERIC(
        tap : INTEGER := 256;
        logtap : INTEGER := 8
    );
    PORT(
        phase : IN signed(15 DOWNTO 0);
        freq : OUT signed(15 DOWNTO 0);

        Clk : IN std_logic;
        Reset : IN std_logic
    );
END phase2freq;

ARCHITECTURE bhvr OF phase2freq IS
    SIGNAL last_phase : signed(15 DOWNTO 0);
    SIGNAL diffrence : signed(15 DOWNTO 0);
    SIGNAL frequency : signed(15 DOWNTO 0);
    SIGNAL frequency_avg : signed(15 + logtap DOWNTO 0) := (OTHERS => '0');
    TYPE reg IS ARRAY(0 TO tap - 1) OF signed(15 DOWNTO 0);
    SIGNAL frequency_reg : reg := (OTHERS => x"0000");
BEGIN
    -- find direvative of phase
    -- tackle wrapping of phase
    -- smooth the output
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            diffrence <= phase - last_phase;
            last_phase <= phase;
            freq <= frequency;
        END IF;
    END PROCESS;

    frequency <= diffrence IF diffrence < 8192 AND diffrence > -8192
                    ELSE frequency_avg(15 + logtap DOWNTO logtap);

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            frequency_reg(0) <= frequency;
            frequency_avg <= frequency_avg - ((logtap - 1 DOWNTO 0 => frequency_reg(tap - 1)(15)) & frequency_reg(tap - 1)) + ((logtap - 1 DOWNTO 0 => frequency(15)) & frequency);
        END IF;
    END PROCESS;

    avg : FOR i IN 0 TO tap - 2 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                frequency_reg(i + 1) <= frequency_reg(i);
            END IF;
        END PROCESS;
    END GENERATE avg;
END bhvr;