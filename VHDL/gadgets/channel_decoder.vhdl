-- Refer to channel_encoder.vhdl for details

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;
/*
ENTITY channel_decoder IS
    PORT(
        I : IN signed(15 DOWNTO 0);
        A : OUT signed(15 DOWNTO 0);
        B : OUT signed(15 DOWNTO 0);
        Reset : IN std_logic;
        Clk : IN std_logic
    );
END channel_decoder;

ARCHITECTURE bhvr OF channel_decoder IS
    signal last_input : signed(15 DOWNTO 0) := (others => '0');
    signal sync : std_logic := '0';
    signal parity : std_logic := '0';
BEGIN
    PROCESS(Clk, Reset)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                A <= (others => '0');
                B <= (others => '0');
                parity <= '0';
                last_input <= (others => '0');
            ELSE
                IF sync = '1' THEN
                    parity <= '0';
                ELSE
                    parity <= not parity;
                END IF;
                IF parity = '0' THEN
                    A <= I;
                ELSE
                    B <= I;
                END IF;
                last_input <= I;
            END IF;
        END IF;
    END PROCESS;

    sync <= '1' WHEN last_input = x"4000" and I = x"B000" ELSE '0';
END bhvr;
*/

ENTITY channel_decoder IS
    PORT(
        phase : IN std_logic;
        I : IN signed(15 DOWNTO 0);
        A : OUT signed(15 DOWNTO 0);
        B : OUT signed(15 DOWNTO 0);
        Reset : IN std_logic;
        Clk : IN std_logic
    );
END channel_decoder;

ARCHITECTURE bhvr OF channel_decoder IS
    SIGNAL parity : std_logic := '0';
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                A <= (others => '0');
                B <= (others => '0');
                parity <= '0';
            ELSE
                parity <= not parity;
                IF parity = phase THEN
                    A <= I;
                ELSE
                    B <= I;
                END IF;
            END IF;
        END IF;
    END PROCESS;
END bhvr;