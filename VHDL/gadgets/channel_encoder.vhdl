-- A Moku MMC module only supports two input channels
-- In order to allow three inputs, mix two of them in a ddr-like style
-- This will cut half the bandwidth of the input signals, but it's fine for power signals

-- Signal from the first channel is transmitted in the even samples, and the second channel in the odd samples
-- A synchronization is made every N samples, to ensure that the signals are in phase
-- Synchronization is done by sending x"4000" and then x"B000" in two consecutive samples, which should not happen in the input signals

-- The above method is deprecated.
-- Instead of synchronizing the signals, manually adjust the parity at the decoder side

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY channel_encoder IS
    PORT(
        sync_period : IN unsigned(15 DOWNTO 0);
        A : IN signed(15 DOWNTO 0);
        B : IN signed(15 DOWNTO 0);
        O : OUT signed(15 DOWNTO 0);
        Reset : IN std_logic;
        Clk : IN std_logic
    );
END channel_encoder;
/*
ARCHITECTURE bhvr OF channel_encoder IS
    SIGNAL counter : unsigned(15 DOWNTO 0) := (OTHERS => '0');
    SIGNAL sync : std_logic := '0';
    SIGNAL last_sync : std_logic := '0';
    SIGNAL parity : std_logic := '0';
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                counter <= (OTHERS => '0');
                sync <= '0';
                last_sync <= '0';
                parity <= '0';
            ELSE
                IF counter = sync_period THEN
                    sync <= '1';
                    parity <= '0';
                    counter <= (OTHERS => '0');
                ELSE
                    sync <= '0';
                    parity <= NOT parity;
                    counter <= counter + 1;
                END IF;
                last_sync <= sync;
            END IF;
        END IF;
    END PROCESS;

    O <= x"4000" WHEN sync = '1' ELSE
            x"B000" WHEN last_sync = '1' ELSE
            A WHEN parity = '0' ELSE
            B;
END bhvr;
*/
ARCHITECTURE bhvr OF channel_encoder IS
    SIGNAL parity : std_logic := '0';
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                parity <= '0';
            ELSE
                parity <= NOT parity;
            END IF;
        END IF;
    END PROCESS;

    O <= A WHEN parity = '0' ELSE B;
END bhvr;