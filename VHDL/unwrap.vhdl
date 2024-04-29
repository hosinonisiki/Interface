LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY unwrap IS
    GENERIC(
        word_length : INTEGER := 16
    );
    PORT(
        input : IN signed(word_length - 1 DOWNTO 0);
        output : OUT signed(2 * word_length - 1 DOWNTO 0);
        Clk : IN std_logic;
        Reset : IN std_logic
    );
END ENTITY unwrap;

ARCHITECTURE bhvr OF unwrap IS
    SIGNAL last : signed(word_length - 1 DOWNTO 0);
    SIGNAL result : signed(2 * word_length - 1 DOWNTO 0);
BEGIN
    PROCESS(Clk)
        VARIABLE temp : signed(word_length - 1 DOWNTO 0);
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                result <= ((word_length - 1 DOWNTO 0 => input(word_length - 1))) & input;
            ELSE
                temp := input - last;
                result <= result + ((word_length - 1 DOWNTO 0 => temp(word_length - 1)) & temp);
            END IF;
            last <= input;
        END IF;
    END PROCESS;
    output <= result;
END ARCHITECTURE bhvr;