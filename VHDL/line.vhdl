LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

PACKAGE MyPak_line IS
    TYPE signs IS ARRAY(NATURAL RANGE <>) OF std_logic;
    TYPE LUT_32 IS ARRAY(NATURAL RANGE <>) OF unsigned(31 DOWNTO 0);
    TYPE LUT_16 IS ARRAY(NATURAL RANGE <>) OF unsigned(15 DOWNTO 0);
    TYPE LUT_48 IS ARRAY(NATURAL RANGE <>) OF unsigned(47 DOWNTO 0);
END PACKAGE;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

USE WORK.MyPak_line.ALL;

ENTITY line IS
    GENERIC(
        segments : INTEGER := 8 -- upper limit of segments
    );
    PORT(
        offset : IN signed(15 DOWNTO 0);

        LUT_sign : IN signs(0 TO segments - 1);
        LUT_x : IN LUT_32(0 TO segments - 1);
        LUT_y : IN LUT_16(0 TO segments - 1);
        LUT_slope : IN LUT_16(0 TO segments - 1);

        segments_enabled : IN INTEGER;

        output : OUT signed(15 DOWNTO 0);
        -- initiate = '0' represents for periodic operation
        -- A '0' peak on initiate represents for single operation
        initiate : IN std_logic;
        prolong : IN std_logic;
        Reset : IN std_logic;
        Clk : IN std_logic
    );
END line;

ARCHITECTURE bhvr OF line IS
    TYPE state IS (standby, running);
    SIGNAL current_state : state := standby;
    SIGNAL x_counter : unsigned(31 DOWNTO 0);
    SIGNAL y_counter : unsigned(15 DOWNTO 0);
    SIGNAL x_accum : unsigned(47 DOWNTO 0);
    SIGNAL y_accum : unsigned(47 DOWNTO 0);

    SIGNAL LUT_slp_mul_x : LUT_48(0 TO segments - 1);

    SIGNAL sign : std_logic;
    SIGNAL x : unsigned(31 DOWNTO 0);
    SIGNAL y : unsigned(15 DOWNTO 0);
    SIGNAL slope : unsigned(15 DOWNTO 0);
    SIGNAL slp_mul_x : unsigned(47 DOWNTO 0);

    SIGNAL y0 : signed(15 DOWNTO 0);

    SIGNAL waveform : signed(15 DOWNTO 0) := (OTHERS => '0');

    SIGNAL next_segment : INTEGER;

    SIGNAL startup : std_logic := '0';
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                waveform <= (OTHERS => '0');
                current_state <= standby;
            ELSIF startup = '1' THEN
                CASE current_state IS
                    WHEN standby =>
                        IF initiate = '0' THEN
                            current_state <= running;
                        END IF;
                        y0 <= (OTHERS => '0');
                        waveform <= (OTHERS => '0');
                        next_segment <= 1;
                        x_counter <= x"00000000";
                        y_counter <= x"0000";
                        x_accum <= x"00000000" & LUT_y(0);
                        y_accum <= LUT_slp_mul_x(0) + (x"0000" & LUT_x(0));
                        sign <= LUT_sign(0);
                        x <= LUT_x(0);
                        y <= LUT_y(0);
                        slope <= LUT_slope(0);
                        slp_mul_x <= LUT_slp_mul_x(0);
                    WHEN running =>
                        IF x_counter = x - x"00000001" THEN
                            IF next_segment = segments_enabled THEN
                                IF initiate = '1' THEN
                                    current_state <= standby;
                                ELSE
                                    IF prolong = '0' THEN
                                        IF sign = '1' THEN
                                            y0 <= y0 - signed(y);
                                        ELSE
                                            y0 <= y0 + signed(y);
                                        END IF;
                                    ELSE
                                        y0 <= (OTHERS => '0');
                                    END IF;
                                    waveform <= (OTHERS => '0');
                                    next_segment <= 1;
                                    x_counter <= x"00000000";
                                    y_counter <= x"0000";
                                    x_accum <= x"00000000" & LUT_y(0);
                                    y_accum <= LUT_slp_mul_x(0) + (x"0000" & LUT_x(0));
                                    sign <= LUT_sign(0);
                                    x <= LUT_x(0);
                                    y <= LUT_y(0);
                                    slope <= LUT_slope(0);
                                    slp_mul_x <= LUT_slp_mul_x(0);
                                END IF;
                            ELSE
                                IF sign = '1' THEN
                                    y0 <= y0 - signed(y);
                                ELSE
                                    y0 <= y0 + signed(y);
                                END IF;
                                next_segment <= next_segment + 1;
                                x_counter <= x"00000000";
                                y_counter <= x"0000";
                                x_accum <= x"00000000" & LUT_y(next_segment);
                                y_accum <= LUT_slp_mul_x(next_segment) + (x"0000" & LUT_x(next_segment));
                                sign <= LUT_sign(next_segment);
                                x <= LUT_x(next_segment);
                                y <= LUT_y(next_segment);
                                slope <= LUT_slope(next_segment);
                                slp_mul_x <= LUT_slope(next_segment) * LUT_x(next_segment);
                            END IF;
                        ELSE
                            IF y_accum > x_accum THEN
                                y_counter <= y_counter + slope;
                                y_accum <= y_accum + slp_mul_x;
                            ELSE
                                y_counter <= y_counter + slope + x"0001";
                                y_accum <= y_accum + slp_mul_x + (x"0000" & x);
                            END IF;
                            x_counter <= x_counter + x"00000001";
                            x_accum <= x_accum + (x"00000000" & y);
                        END IF;
                        IF sign = '1' THEN
                            waveform <= y0 - signed(y_counter);
                        ELSE
                            waveform <= y0 + signed(y_counter);
                        END IF;
                END CASE;
            END IF;
        END IF;
    END PROCESS;

    gen : FOR i IN 0 TO segments - 1 GENERATE
        LUT_slp_mul_x(i) <= LUT_slope(i) * LUT_x(i);
    END GENERATE gen;

    PROCESS(Reset)
    BEGIN
        IF falling_edge(Reset) THEN
            startup <= '1';
        END IF;
    END PROCESS;

    output <= offset + waveform;
END bhvr;