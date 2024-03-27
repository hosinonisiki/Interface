LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

USE WORK.MyPak_line.ALL;

ENTITY AWG IS
    PORT(
        frequency_bias : IN unsigned(15 DOWNTO 0);
        -- frequency control parameters
        set_sign : IN std_logic;
        set_x : IN unsigned(31 DOWNTO 0);
        set_y : IN unsigned(15 downto 0);
        set_slope : IN unsigned(15 DOWNTO 0);
        set_address : IN unsigned(3 DOWNTO 0);
        set : IN std_logic;

        segments_enabled : IN unsigned(3 DOWNTO 0); -- 0~7 + 1 = 1~8
        initiate : IN std_logic;
        periodic : IN std_logic;
        prolong : IN std_logic;

        amplitude : IN signed(15 DOWNTO 0);

        outputC : OUT signed(15 DOWNTO 0);
        outputS : OUT signed(15 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END AWG;

ARCHITECTURE bhvr OF AWG IS
    SIGNAL frequency : unsigned(15 DOWNTO 0);
    SIGNAL waveformC : signed(15 DOWNTO 0);
    SIGNAL waveformS : signed(15 DOWNTO 0);
    SIGNAL outputC_buf : signed(31 DOWNTO 0);
    SIGNAL outputS_buf : signed(31 DOWNTO 0);

    SIGNAL LUT_sign : signs(0 TO 7);
    SIGNAL LUT_x : LUT_32(0 TO 7);
    SIGNAL LUT_y : LUT_16(0 TO 7);
    SIGNAL LUT_slope : LUT_16(0 TO 7);

    SIGNAL buf_sign : std_logic_vector(0 DOWNTO 0);

    SIGNAL memory_sign : std_logic_vector(7 DOWNTO 0);
    SIGNAL memory_x : std_logic_vector(255 DOWNTO 0);
    SIGNAL memory_y : std_logic_vector(127 DOWNTO 0);
    SIGNAL memory_slope : std_logic_vector(127 DOWNTO 0);

    SIGNAL segments_enabled_translated : INTEGER RANGE 1 TO 8;
    SIGNAL slope_calculated : unsigned(15 DOWNTO 0);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            outputC <= outputC_buf(31 DOWNTO 16);
            outputS <= outputS_buf(31 DOWNTO 16);
        END IF;
    END PROCESS;

    buf_sign <= (0 => set_sign); -- verbose due to 2002 standard

    sign_mem : ENTITY WORK.writer GENERIC MAP(
        size => 8,
        word_length => 1
    )PORT MAP(
        data => buf_sign,
        address => to_integer(set_address),
        write => set,
        memory => memory_sign,

        Reset => Reset,
        Clk => Clk
    );

    x_mem : ENTITY WORK.writer GENERIC MAP(
        size => 8,
        word_length => 32
    )PORT MAP(
        data => std_logic_vector(set_x),
        address => to_integer(set_address),
        write => set,
        memory => memory_x,

        Reset => Reset,
        Clk => Clk
    );

    y_mem : ENTITY WORK.writer GENERIC MAP(
        size => 8,
        word_length => 16
    )PORT MAP(
        data => std_logic_vector(set_y),
        address => to_integer(set_address),
        write => set,
        memory => memory_y,

        Reset => Reset,
        Clk => Clk
    );

    slope_mem : ENTITY WORK.writer GENERIC MAP(
        size => 8,
        word_length => 16
    )PORT MAP(
        data => std_logic_vector(set_slope),
        address => to_integer(set_address),
        write => set,
        memory => memory_slope,

        Reset => Reset,
        Clk => Clk
    );

    type_conversion : FOR i IN 0 TO 7 GENERATE
        LUT_sign(i) <= memory_sign(i);
        LUT_x(i) <= unsigned(memory_x(i * 32 + 31 DOWNTO i * 32));
        LUT_y(i) <= unsigned(memory_y(i * 16 + 15 DOWNTO i * 16));
        LUT_slope(i) <= unsigned(memory_slope(i * 16 + 15 DOWNTO i * 16));
    END GENERATE;

    segments_enabled_translated <= to_integer(segments_enabled) + 1; -- verbose due to 2002 standard

    frequency_control : ENTITY WORK.line_unsigned GENERIC MAP(
        segments => 8
    )PORT MAP(
        offset => frequency_bias,

        LUT_sign => LUT_sign,
        LUT_x => LUT_x,
        LUT_y => LUT_y,
        LUT_slope => LUT_slope,

        segments_enabled => segments_enabled_translated,

        output => frequency,

        initiate => initiate,
        periodic => periodic,
        prolong => prolong,
        Reset => Reset,
        Clk => Clk
    );

    slope_calculated <= x"0" & frequency(15 DOWNTO 4); -- verbose due to 2002 standard

    WG : ENTITY WORK.WaveGen PORT MAP(
        init_phase => x"0000",
        time_step => x"00000010", -- range 0 to 19.53125MHz, step 298.023Hz
        phase_step => frequency,
        slope => slope_calculated,

        outputC => waveformC,
        outputS => waveformS,

        Reset => Reset,
        Clk => Clk
    );

    outputC_buf <= amplitude * waveformC;
    outputS_buf <= amplitude * waveformS;
END bhvr;