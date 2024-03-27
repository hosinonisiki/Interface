LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY writer IS
    GENERIC(
        size : INTEGER := 8;
        word_length : INTEGER := 16
    );
    PORT(
        -- data : MSB ... LSB MSB ... LSB MSB ... LSB 0
        -- address:    2           1           0  
        data : IN std_logic_vector(word_length - 1 DOWNTO 0);
        address : IN INTEGER RANGE 0 TO size - 1;
        write : IN std_logic;
        memory : OUT std_logic_vector(size * word_length - 1 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END writer;

ARCHITECTURE bhvr OF writer IS
    CONSTANT default_memory : std_logic_vector(size * word_length - 1 DOWNTO 0) := (OTHERS => '0');
    SIGNAL memory_internal : std_logic_vector(size * word_length - 1 DOWNTO 0) := default_memory;

    SIGNAL last_write : std_logic := '0';
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                memory_internal <= default_memory;
            ELSIF write = '0' AND last_write = '1' THEN
                memory_internal((address + 1) * word_length - 1 DOWNTO address * word_length) <= data;
            END IF;
            memory <= memory_internal;
            last_write <= write;
        END IF;
    END PROCESS;
END bhvr;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY reader IS
    GENERIC(
        size : INTEGER := 8;
        word_length : INTEGER := 16
    );
    PORT(
        address : IN INTEGER RANGE 0 TO size - 1;
        read : IN std_logic;
        memory : IN std_logic_vector(size * word_length - 1 DOWNTO 0);
        data : OUT std_logic_vector(word_length - 1 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END reader;

ARCHITECTURE bhvr OF reader IS
    SIGNAL memory_internal : std_logic_vector(size * word_length - 1 DOWNTO 0);

    SIGNAL last_read : std_logic := '0';
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                data <= (OTHERS => '0');
            ELSIF read = '0' AND last_read = '1' THEN
                data <= memory_internal((address + 1) * word_length - 1 DOWNTO address * word_length);
            END IF;
            memory_internal <= memory;
            last_read <= read;
        END IF;
    END PROCESS;
END bhvr;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

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
    SIGNAL memory : std_logic_vector(size * word_length - 1 DOWNTO 0);
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
