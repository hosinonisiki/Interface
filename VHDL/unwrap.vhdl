LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY unwrap IS
    GENERIC(
        word_length : INTEGER := 16;
        unwrapped_word_length : INTEGER := 17
    );
    PORT(
        input : IN signed(word_length - 1 DOWNTO 0);
        unwrapped : OUT signed(unwrapped_word_length - 1 DOWNTO 0);
        clamped : OUT signed(word_length - 1 DOWNTO 0);
        Clk : IN std_logic;
        Reset : IN std_logic
    );
END ENTITY unwrap;

-- for a signal that wraps around, it's hard to tell which way it's wrapping when the sign bit flips
-- in order to tell apart the two cases, we add an extra bit to the signal, so that the 2 MSBs indicate the direction of wrapping

ARCHITECTURE bhvr OF unwrap IS
    CONSTANT extra_bit : INTEGER := unwrapped_word_length - word_length;
    SIGNAL period_counter : signed(extra_bit - 1 DOWNTO 0); -- this signal is used to keep track of how many times the signal has wrapped around, and will also serve as the MSBs of the unwrapped signal
    SIGNAL last : signed(word_length - 1 DOWNTO 0);
    SIGNAL first_unwrap : signed(word_length DOWNTO 0); -- this signal unwraps the input for 1 single time to check the direction of wrapping
    SIGNAL wrap_indicator : signed(1 DOWNTO 0); -- this signal indicates the direction of wrapping
    SIGNAL last_wrap_indicator : signed(1 DOWNTO 0);
    SIGNAL reg_LSB : signed(word_length - 1 DOWNTO 0);
    SIGNAL result : signed(unwrapped_word_length - 1 DOWNTO 0);
BEGIN
    PROCESS(Clk)
        VARIABLE temp : signed(word_length - 1 DOWNTO 0);
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                first_unwrap <= input(word_length - 1) & input;
            ELSE
                temp := input - last;
                first_unwrap <= first_unwrap + (temp(word_length - 1) & temp);
            END IF;
            last <= input;
        END IF;
    END PROCESS;

    wrap_indicator <= first_unwrap(word_length DOWNTO word_length - 1);
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                period_counter <= (others => first_unwrap(word_length));
            ELSE
                IF ((wrap_indicator = "00" AND last_wrap_indicator = "11") OR (wrap_indicator = "10" AND last_wrap_indicator = "01")) AND period_counter /= 2 ** (extra_bit - 1) - 1 THEN
                    period_counter <= period_counter + 1;
                END IF;
                IF ((wrap_indicator = "11" AND last_wrap_indicator = "00") OR (wrap_indicator = "01" AND last_wrap_indicator = "10")) AND period_counter /= - 2 ** (extra_bit - 1) THEN
                    period_counter <= period_counter - 1;
                END IF;
            END IF;
            reg_LSB <= first_unwrap(word_length - 1 DOWNTO 0);
            last_wrap_indicator <= wrap_indicator;
        END IF;
    END PROCESS;

    result <= period_counter & reg_LSB;
    unwrapped <= result;
    clamped <= '0' & (word_length - 2 DOWNTO 0 => '1') WHEN result >= 2 ** (word_length - 1) ELSE
                '1' & (word_length - 2 DOWNTO 0 => '0') WHEN result <= - 2 ** (word_length - 1) ELSE
                reg_LSB;
END ARCHITECTURE bhvr;