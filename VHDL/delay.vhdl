LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY delay IS
    GENERIC(
        word_length : INTEGER := 16;
        cycles : INTEGER
    );
    PORT(
        din : IN std_logic_vector(word_length - 1 DOWNTO 0);
        dout : OUT std_logic_vector(word_length - 1 DOWNTO 0);
        Clk : IN std_logic
    );
END delay;

ARCHITECTURE bhvr OF delay IS
    TYPE reg_array IS ARRAY(0 TO cycles) OF std_logic_vector(word_length - 1 DOWNTO 0);
    SIGNAL regs : reg_array := (others => (others => '0'));
    SIGNAL read_index : INTEGER := 0;
    SIGNAL write_index : INTEGER := cycles;
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF write_index = cycles THEN
                write_index <= 0;
            ELSE
                write_index <= write_index + 1;
            END IF;
            IF read_index = cycles THEN
                read_index <= 0;
            ELSE
                read_index <= read_index + 1;
            END IF;
            regs(write_index) <= din;
            dout <= regs(read_index);
        END IF;
    END PROCESS;
END bhvr;