LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

USE WORK.MyPak_line.ALL;

ENTITY WaveGen IS
    PORT(
        init_phase : IN signed(15 DOWNTO 0);
        time_step : IN unsigned(31 DOWNTO 0);
        phase_step : IN unsigned(15 DOWNTO 0);
        slope : IN unsigned(15 DOWNTO 0);

        outputC : OUT signed(15 DOWNTO 0);
        outputS : OUT signed(15 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END WaveGen;

ARCHITECTURE bhvr OF WaveGen IS
    SIGNAL phase : signed(15 DOWNTO 0);
    SIGNAL waveform : signed(15 DOWNTO 0);

    SIGNAL LUT_sign_input : signs(0 DOWNTO 0);
    SIGNAL LUT_x_input : LUT_32(0 DOWNTO 0);
    SIGNAL LUT_y_input : LUT_16(0 DOWNTO 0);
    SIGNAL LUT_slope_input : LUT_16(0 DOWNTO 0);
BEGIN
    LUT_sign_input <= (0 => '0'); -- verbose due to 2002 standard
    LUT_x_input <= (0 => time_step);
    LUT_y_input <= (0 => phase_step);
    LUT_slope_input <= (0 => slope);

    -- generate a linear phase signal which wraps around at +/- pi
    phase_control : ENTITY WORK.line_signed GENERIC MAP(
        segments => 1
    )PORT MAP(
        offset => init_phase,
        
        LUT_sign => LUT_sign_input,
        LUT_x => LUT_x_input,
        LUT_y => LUT_y_input,
        LUT_slope => LUT_slope_input,

        segments_enabled => 1,

        working => OPEN,
        current => OPEN,
        output => phase,
        initiate => Reset,
        prolong => '0',
        periodic => '0',
        Reset => Reset,
        Clk => Clk
    );

    waveform_control : ENTITY WORK.sincos PORT MAP(
        input => phase,
        outputC => outputC,
        outputS => outputS,
        Clk => Clk
    );
END bhvr;
