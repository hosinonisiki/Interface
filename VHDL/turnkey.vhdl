LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

PACKAGE MyPak_turnkey IS
    TYPE signs IS ARRAY(NATURAL RANGE <>) OF std_logic;
    TYPE LUT_24 IS ARRAY(NATURAL RANGE <>) OF unsigned(23 DOWNTO 0);
    TYPE LUT_16 IS ARRAY(NATURAL RANGE <>) OF unsigned(15 DOWNTO 0);
    TYPE LUT_40 IS ARRAY(NATURAL RANGE <>) OF unsigned(39 DOWNTO 0);
END PACKAGE;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

USE WORK.MyPak_turnkey.ALL;

-- todo : replace the implement of line state with line entity
-- todo : replace averaging with an entity
ENTITY turnkey IS
    GENERIC(
        segments : INTEGER := 3; -- enumerated from 1, but array index starts at 0
        tap : INTEGER := 64; -- for calculating moving averages
        logtap : INTEGER := 6
    );
    PORT(
        soliton_power_unscaled : IN signed(15 DOWNTO 0);
        scanning_voltage_scaled : OUT signed(15 DOWNTO 0);

        hold_period : IN unsigned(23 DOWNTO 0);
        max_voltage : IN signed(15 DOWNTO 0);
        min_voltage : IN signed(15 DOWNTO 0);
        step_voltage : IN signed(15 DOWNTO 0); -- step_voltage is positive but indicates a downward scanning procedure by default
        soliton_threshold_max : IN signed(15 DOWNTO 0);
        soliton_threshold_min : IN signed(15 DOWNTO 0);
        
        LUT_sign : IN signs(0 TO segments - 1);
        LUT_period : IN LUT_24(0 TO segments - 1);
        LUT_amplitude : IN LUT_16(0 TO segments - 1);
        LUT_slope : IN LUT_16(0 TO segments - 1);

        attempts : IN unsigned(7 DOWNTO 0);
        approaches : IN unsigned(7 DOWNTO 0);
        
        coarse_target : IN signed(15 DOWNTO 0);
        fine_target : IN signed(15 DOWNTO 0);

        coarse_period : IN unsigned(23 DOWNTO 0);
        fine_period : IN unsigned(23 DOWNTO 0);

        stab_target : IN signed(15 DOWNTO 0);
        stab_period : IN unsigned(23 DOWNTO 0);

        floor : IN signed(15 DOWNTO 0);

        PID_K_P : IN signed(31 DOWNTO 0);
        PID_K_I : IN signed(31 DOWNTO 0);
        PID_K_D : IN signed(31 DOWNTO 0);

        mode : IN std_logic;

        sweep_period : IN unsigned(23 DOWNTO 0);
        
        PID_limit_sum : IN signed(15 DOWNTO 0);

        PID_lock : IN std_logic;

        input_gain : IN signed(7 DOWNTO 0);
        output_gain : IN signed(7 DOWNTO 0);

        manual_offset : IN signed(15 DOWNTO 0);

        Clk : IN std_logic;
        Reset : IN std_logic;

        TestA : OUT signed(15 DOWNTO 0);
        TestB : OUT signed(15 DOWNTO 0)
    );
END turnkey;

ARCHITECTURE bhvr OF turnkey IS
    SIGNAL soliton_power : signed(15 DOWNTO 0);
    SIGNAL scanning_voltage : signed(15 DOWNTO 0);
    SIGNAL reg_scanning_voltage : signed(15 DOWNTO 0);
    SIGNAL reg_soliton_power : signed(23 DOWNTO 0);
    SIGNAL reg_scanning_voltage_scaled : signed(23 DOWNTO 0);

    TYPE state IS (standby, confirm, line, hold, failure, coarse, fine, stablize, longterm, sweep, sweeppause);
    SIGNAL current_state : state := standby;
    SIGNAL platform_voltage : signed(15 DOWNTO 0);
    SIGNAL output_voltage : signed(15 DOWNTO 0) := x"0000";
    SIGNAL period_counter : unsigned(23 DOWNTO 0);
    SIGNAL amplitude_counter : unsigned(15 DOWNTO 0);

    SIGNAL period_accum : unsigned(39 DOWNTO 0); -- variables for line drawing. This one adds up amplitude recursively for period times

    SIGNAL amplitude_accum : unsigned(39 DOWNTO 0);

    SIGNAL next_segment : INTEGER := 1;

    SIGNAL period : unsigned(23 DOWNTO 0);
    SIGNAL amplitude : unsigned(15 DOWNTO 0);
    SIGNAL slope : unsigned(15 DOWNTO 0);

    SIGNAL offset_voltage : signed(15 DOWNTO 0);
    SIGNAL sign : std_logic;

    SIGNAL LUT_slp_mul_prd : LUT_40(0 TO segments - 1);

    SIGNAL attempt_counter : unsigned(7 DOWNTO 0);
    SIGNAL approach_counter : unsigned(7 DOWNTO 0);

    SIGNAL none_counter : unsigned(23 DOWNTO 0);
    SIGNAL soliton_counter : unsigned(23 DOWNTO 0);
    SIGNAL MI_counter : unsigned(23 DOWNTO 0);

    SIGNAL soliton_detected : std_logic := '0';
    SIGNAL MI_detected : std_logic := '0';
    SIGNAL soliton_failure : std_logic := '0';

    SIGNAL soliton_power_avg : signed(15 + logtap DOWNTO 0) := (OTHERS => '0');
    TYPE reg IS ARRAY(0 TO tap - 1) OF signed(15 DOWNTO 0);
    SIGNAL soliton_power_reg : reg := (OTHERS => x"0000");

    SIGNAL stab_counter : signed(15 DOWNTO 0);

    SIGNAL PID_setpoint : signed(15 DOWNTO 0);
    SIGNAL PID_control : signed(15 DOWNTO 0);
    SIGNAL PID_reset : std_logic := '1';

    SIGNAL startup : std_logic := '0';
    -- loaded parameters stay unchanged during operation

BEGIN
    -- IO
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
        soliton_power <= reg_soliton_power(19 DOWNTO 4);
            scanning_voltage_scaled <= reg_scanning_voltage_scaled(19 DOWNTO 4);
            scanning_voltage <= reg_scanning_voltage;
        END IF;
    END PROCESS;
    reg_soliton_power <= soliton_power_unscaled * input_gain;
    reg_scanning_voltage_scaled <= scanning_voltage * output_gain;
    
    -- FSM
    PROCESS(Clk)
    BEGIN
         IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                -- reset
                output_voltage <= max_voltage; --
                current_state <= standby; --
            ELSIF startup = '1' THEN
                -- no events on Reset
                CASE current_state IS
                    WHEN standby =>
                        IF mode = '1' THEN
                            -- sweep
                            period_counter <= x"000000";
                            output_voltage <= x"0000";
                            current_state <= sweep;
                        ELSE
                            -- set
                            soliton_detected <= '0';
                            MI_detected <= '0';
                            soliton_failure <= '0';
                            platform_voltage <= max_voltage; --
                            attempt_counter <= x"00";
                            approach_counter <= x"01";
                            current_state <= confirm; --
                        END IF;
                    WHEN confirm => 
                        IF soliton_detected = '1' THEN
                            -- success
                            soliton_detected <= '0';
                            period_counter <= x"000000";
                            current_state <= coarse; --
                        ELSIF platform_voltage <= min_voltage OR MI_detected = '1' OR soliton_failure = '1' THEN
                            -- another approach
                            IF approach_counter = approaches THEN
                                --failure
                                current_state <= failure;
                            ELSE
                                --pull out
                                --high voltage
                                platform_voltage <= max_voltage; --
                                MI_detected <= '0';
                                soliton_failure <= '0';
                                attempt_counter <= x"00";
                                approach_counter <= approach_counter + x"01";
                            END IF;
                        ELSE
                            -- keep scanning. notice that this takes an extra cycle
                            IF attempt_counter = attempts THEN
                                platform_voltage <= platform_voltage - step_voltage; --
                                offset_voltage <= platform_voltage - step_voltage;
                                attempt_counter <= x"00";
                            ELSE
                                offset_voltage <= platform_voltage;
                                attempt_counter <= attempt_counter + x"01";
                            END IF;
                            next_segment <= 1;
                            period_counter <= x"000000"; --
                            amplitude_counter <= x"0000"; --
                            period_accum <= x"000000" & LUT_amplitude(0); --
                            amplitude_accum <= LUT_slp_mul_prd(0) + (x"0000" & LUT_period(0)); --
                            period <= LUT_period(0);
                            amplitude <= LUT_amplitude(0);
                            slope <= LUT_slope(0);
                            sign <= LUT_sign(0);
                            current_state <= line; --
                            PID_reset <= '1';
                        END IF;
                    WHEN line =>
                        IF period_counter = period - x"000001" THEN
                            IF next_segment = segments THEN
                                --enter hold
                                period_counter <= x"000000";
                                none_counter <= x"000000";
                                soliton_counter <= x"000000";
                                MI_counter <= x"000000";
                                current_state <= hold;
                            ELSE
                                next_segment <= next_segment + 1;
                                period_counter <= x"000000";
                                amplitude_counter <= x"0000";
                                period_accum <= x"000000" & LUT_amplitude(next_segment);
                                amplitude_accum <= LUT_slp_mul_prd(next_segment) + (x"0000" & LUT_period(next_segment));
                                period <= LUT_period(next_segment);
                                amplitude <= LUT_amplitude(next_segment);
                                slope <= LUT_slope(next_segment);
                                sign <= LUT_sign(next_segment);
                                IF sign = '1' THEN
                                    offset_voltage <= offset_voltage - signed(amplitude);
                                ELSE
                                    offset_voltage <= offset_voltage + signed(amplitude);
                                END IF;
                            END IF;
                        ELSE
                            IF amplitude_accum > period_accum THEN
                                amplitude_counter <= amplitude_counter + slope;
                                amplitude_accum <= amplitude_accum + LUT_slp_mul_prd(next_segment - 1);
                            ELSE
                                amplitude_counter <= amplitude_counter + slope + x"0001";
                                amplitude_accum <= amplitude_accum + LUT_slp_mul_prd(next_segment - 1) + (x"0000" & period);
                            END IF;
                            period_counter <= period_counter + x"000001";
                            period_accum <= period_accum + (x"000000" & amplitude);
                        END IF;
                        IF sign = '1' THEN
                            output_voltage <= offset_voltage - signed(amplitude_counter);
                        ELSE
                            output_voltage <= offset_voltage + signed(amplitude_counter);
                        END IF;
                    WHEN hold => 
                        IF period_counter = hold_period - x"000001" THEN
                            IF MI_counter >= soliton_counter AND MI_counter > none_counter THEN
                                MI_detected <= '1';
                            ELSIF soliton_counter > none_counter THEN
                                soliton_detected <= '1';
                            END IF;
                            current_state <= confirm; --
                        END IF;
                        IF soliton_power >= soliton_threshold_max THEN
                            MI_counter <= MI_counter + x"000001";
                        ELSIF soliton_power <= soliton_threshold_min THEN
                            none_counter <= none_counter + x"000001";
                        ELSE
                            soliton_counter <= soliton_counter + x"000001";
                        END IF;
                        period_counter <= period_counter + x"000001"; --
                        output_voltage <= platform_voltage; --
                    WHEN failure =>
                        output_voltage <= max_voltage;
                    WHEN coarse =>
                        IF period_counter = coarse_period - x"000001" THEN
                            IF soliton_power_avg(15 + logtap DOWNTO logtap) > coarse_target THEN -- need also to consider the situation where the soliton fails
                                output_voltage <= output_voltage - x"0001";
                            ELSIF soliton_power_avg(15 + logtap DOWNTO logtap) < floor THEN
                                soliton_failure <= '1';
                                current_state <= confirm;
                            ELSE
                                current_state <= fine;
                            END IF;
                            period_counter <= x"000000";
                        ELSE
                            period_counter <= period_counter + x"000001";
                        END IF;
                    WHEN fine =>
                        IF period_counter = fine_period - x"000001" THEN
                            IF soliton_power_avg(15 + logtap DOWNTO logtap) > fine_target THEN
                                output_voltage <= output_voltage - x"0001";
                            ELSIF soliton_power_avg(15 + logtap DOWNTO logtap) < floor THEN
                                soliton_failure <= '1';
                                current_state <= confirm;
                            ELSE
                                stab_counter <= x"0000";
                                current_state <= stablize;
                            END IF;
                            period_counter <= x"000000";
                        ELSE
                            period_counter <= period_counter + x"000001";
                        END IF;
                    WHEN stablize =>
                        IF period_counter = stab_period - x"000001" THEN
                            IF soliton_power_avg(15 + logtap DOWNTO logtap) < floor THEN
                                soliton_failure <= '1';
                                current_state <= confirm;
                            ELSE
                                IF stab_counter < stab_target THEN
                                    stab_counter <= stab_counter + x"0001";
                                    output_voltage <= output_voltage + x"0001";
                                ELSE
                                    --long term
                                    PID_setpoint <= soliton_power_avg(15 + logtap DOWNTO logtap);
                                    current_state <= longterm;
                                END IF;
                            END IF;
                            period_counter <= x"000000";
                        ELSE
                            period_counter <= period_counter + x"000001";
                        END IF;
                    WHEN longterm =>
                        IF soliton_power_avg(15 + logtap DOWNTO logtap) < floor THEN
                            soliton_failure <= '1';
                            current_state <= confirm;
                        END IF;
                        PID_reset <= '0'; 
                    WHEN sweep =>
                        IF period_counter = sweep_period - x"000001" THEN
                            IF output_voltage = max_voltage THEN
                                output_voltage <= x"0000";
                                current_state <= sweeppause;
                            ELSE
                                output_voltage <= output_voltage + x"0001";
                            END IF;
                            period_counter <= x"000000";
                        ELSE
                            period_counter <= period_counter + x"000001";
                        END IF;
                    WHEN sweeppause =>
                        IF period_counter = hold_period - x"000001" THEN
                            period_counter <= x"000000";
                            current_state <= sweep;
                        ELSE
                            period_counter <= period_counter + x"000001";
                        END IF;
                    WHEN OTHERS =>
                END CASE;
            END IF;
         END IF;
    END PROCESS;
    --soliton power average

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            soliton_power_reg(0) <= soliton_power;
            soliton_power_avg <= soliton_power_avg - ((logtap - 1 DOWNTO 0 => soliton_power_reg(tap - 1)(15)) & soliton_power_reg(tap - 1)) + ((logtap - 1 DOWNTO 0 => soliton_power(15)) & soliton_power);
         END IF;
    END PROCESS;
    
    avg : FOR i IN 0 TO tap - 2 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                soliton_power_reg(i + 1) <= soliton_power_reg(i);
            END IF;
        END PROCESS;
    END GENERATE avg;

    pid: ENTITY WORK.PID PORT MAP(
        actual => soliton_power_avg(15 + logtap DOWNTO logtap),
        setpoint => PID_setpoint,
        control => PID_control,

        K_P => PID_K_P,
        K_I => PID_K_I,
        K_D => PID_K_D,

        limit_I => x"0001000000000000",

        limit_sum => PID_limit_sum,

        Reset => PID_reset,
        Clk => Clk
    );

    TestA <= x"0000";
    TestB <= soliton_power_avg(15 + logtap DOWNTO logtap) - PID_setpoint;

    gen : FOR i IN 0 TO segments - 1 GENERATE
        LUT_slp_mul_prd(i) <= LUT_slope(i) * LUT_period(i);
    END GENERATE gen;

    PROCESS(Reset)
    BEGIN
        IF falling_edge(Reset) THEN
            startup <= '1';
        END IF;
    END PROCESS;

    -- Test <= PID_control;
    -- limit wrapping around
    reg_scanning_voltage <= output_voltage + manual_offset + PID_control WHEN current_state = longterm AND PID_lock = '0' ELSE
                        output_voltage + manual_offset;
END bhvr;
