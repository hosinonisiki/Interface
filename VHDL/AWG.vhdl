LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

USE WORK.MyPak_line.ALL;

ENTITY AWG IS
    PORT(
        frequency_bias : IN unsigned(15 DOWNTO 0);
        -- frequency control parameters
        LUT_sign : IN signs(0 TO 7);
        LUT_x : IN LUT_32(0 TO 7);
        LUT_y : IN LUT_16(0 TO 7);
        LUT_slope : IN LUT_16(0 TO 7);
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

    segments_enabled_translated <= to_integer(segments_enabled) + 1; -- verbose due to 2002 standard

    frequency_control : ENTITY WORK.line_unsigned GENERIC MAP(
        segments => 8
    )PORT MAP(
        offset => frequency_bias,

        LUT_sign_input => LUT_sign,
        LUT_x_input => LUT_x,
        LUT_y_input => LUT_y,
        LUT_slope_input => LUT_slope,

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