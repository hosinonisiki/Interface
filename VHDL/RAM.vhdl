LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY writer IS
    GENERIC(
        size : INTEGER := 8;
        word_length : INTEGER := 16
    );
    PORT(
        data : IN std_logic_vector(word_length - 1 DOWNTO 0);
        address : IN INTEGER RANGE 0 TO size - 1;
        write : IN std_logic;
        memory : OUT ARRAY(0 TO size - 1) OF std_logic_vector(word_length - 1 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END writer;

ARCHITECTURE bhvr OF writer IS
    CONSTANT default_memory : ARRAY(0 TO size - 1) OF std_logic_vector(word_length - 1 DOWNTO 0) := (OTHERS => (OTHERS => '0'));
    SIGNAL memory_internal : ARRAY(0 TO size - 1) OF std_logic_vector(word_length - 1 DOWNTO 0) := default_memory;
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                memory_internal <= default_memory;
            ELSIF write = '0' THEN
                memory_internal(address) <= data;
            END IF;
        END IF;
    END PROCESS;

    memory <= memory_internal;
END bhvr;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_1164.ALL;

ENTITY reader IS
    GENERIC(
        size : INTEGER := 8;
        word_length : INTEGER := 16
    );
    PORT(
        address : IN INTEGER RANGE 0 TO size - 1;
        read : IN std_logic;
        memory : IN ARRAY(0 TO size - 1) OF std_logic_vector(word_length - 1 DOWNTO 0);
        data : OUT std_logic_vector(word_length - 1 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END reader;

ARCHITECTURE bhvr OF reader IS
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                data <= (OTHERS => '0');
            ELSIF read = '0' THEN
                data <= memory(address);
            END IF;
        END IF;
    END PROCESS;
END bhvr;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_1164.ALL;

ENTITY RAM IS
    GENERIC(
        size : INTEGER := 8;
        word_length : INTEGER := 16
    );
    PORT(
        data_in : IN std_logic_vector(word_length - 1 DOWNTO 0);
        address_in : IN INTEGER RANGE 0 TO size - 1;
        write : IN std_logic;
        data_out : OUT std_logic_vector(word_length - 1 DOWNTO 0);
        address_out : IN INTEGER RANGE 0 TO size - 1;
        read : IN std_logic;

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END RAM;

ARCHITECTURE bhvr OF RAM IS
    SIGNAL memory : ARRAY(0 TO size - 1) OF std_logic_vector(word_length - 1 DOWNTO 0);
BEGIN
    writing_end : ENTITY WORK.writer GENERIC MAP(
        size => size,
        word_length => word_length
    )PORT MAP(
        data => data_in,
        address => address_in,
        write => write,
        memory => memory,

        Reset => Reset,
        Clk => Clk
    );

    reading_end : ENTITY WORK.reader GENERIC MAP(
        size => size,
        word_length => word_length
    )PORT MAP(
        address => address_out,
        read => read,
        memory => memory,
        data => data_out,

        Reset => Reset,
        Clk => Clk
    );
END bhvr;
