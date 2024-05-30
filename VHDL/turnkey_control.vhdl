LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY turnkey_control IS
    PORT(
        soliton_power : IN signed(15 DOWNTO 0);
        soliton_power_avg : IN signed(15 DOWNTO 0);

        vol_lsr_in : IN signed(15 DOWNTO 0);
        vol_lsr_out : IN IN signed(15 DOWNTO 0);
        vol_vco_in : IN signed(15 DOWNTO 0);
        vol_vco_out : IN signed(15 DOWNTO 0);

        max_vol_lsr : IN signed(15 DOWNTO 0);
        min_vol_lsr : IN signed(15 DOWNTO 0);
        is_lst_seg_lsr : IN std_logic;

        soliton_threshold_max : IN signed(15 DOWNTO 0);
        soliton_threshold_min : IN signed(15 DOWNTO 0);
        detection_time : IN unsigned(31 DOWNTO 0);

        approaches : IN unsigned(7 DOWNTO 0);

        coarse_target : IN signed(15 DOWNTO 0);
        fine_target : IN signed(15 DOWNTO 0);

        coarse_period : IN unsigned(23 DOWNTO 0);
        fine_period : IN unsigned(23 DOWNTO 0);

        stab_target : IN signed(15 DOWNTO 0);
        stab_period : IN unsigned(23 DOWNTO 0);

        floor : IN signed(15 DOWNTO 0);

        detect_soliton : IN std_logic;
        PID_lock : IN std_logic;
        immediate_PID : IN std_logic;

        initiate_lsr : OUT std_logic;
        prolong_lsr : OUT std_logic;
        initiate_vco : OUT std_logic;
        prolong_vco : OUT std_logic;
        
        manual_offset : IN signed(15 DOWNTO 0);

        rst_lsr : OUT std_logic;
        rst_vco : OUT std_logic;

        Clk : IN std_logic;
        Reset : IN std_logic
    );
END turnkey_control;

ARCHITECTURE bhvr OF turnkey_contorl IS
    TYPE state_type IS (s_idle, s_prepare, s_restart, s_scan, s_detect, s_wait, s_coarse, s_fine, s_stabilize, s_longterm, s_failure);
    SIGNAL current_state : state_type := s_idle;

    SIGNAL time_cnt : unsigned(31 DOWNTO 0) := x"00000000";

    SIGNAL approach_counter : unsigned(7 DOWNTO 0) := x"00";

    SIGNAL output_voltage_lsr : signed(15 DOWNTO 0) := (OTHERS => '0');
    SIGNAL output_voltage_vco : signed(15 DOWNTO 0) := (OTHERS => '0');

    SIGNAL none_counter : unsigned(31 DOWNTO 0);
    SIGNAL soliton_counter : unsigned(31 DOWNTO 0);
    SIGNAL MI_counter : unsigned(31 DOWNTO 0);

    SIGNAL MI_detected : std_logic := '0';
    SIGNAL soliton_failure : std_logic := '0';
    SIGNAL minimum_reached : std_logic := '0';

    SIGNAL stab_counter : signed(15 DOWNTO 0);
BEGIN
    -- FSM
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                current_state <= s_idle;
                initiate_lsr <= '1';
                initiate_vco <= '1';
                prolong_lsr <= '1';
                prolong_vco <= '1';
                rst_lsr <= '1';
                rst_vco <= '1';
                approach_counter <= x"00";
                MI_detected <= '0';
                soliton_detected <= '0';
            ELSE
                CASE current_state IS
                    WHEN s_idle =>
                        -- initializations
                        rst_lsr <= '0';
                        rst_vco <= '0';
                        current_state <= s_prepare;
                    WHEN s_prepare =>
                        IF MI_detected = '1' OR soliton_failure = '1' OR minimum_reached = '1' THEN
                            MI_detected <= '0';
                            soliton_failure <= '0';
                            minimum_reached <= '0';
                            IF approach_counter < approaches THEN
                                approach_counter <= approach_counter + x"01";
                            ELSE
                                current_state <= s_failure;
                            END IF;
                        ELSE
                            -- prepare for scanning
                            initiate_lsr <= '0';
                            initiate_vco <= '0';
                            prolong_lsr <= '0';
                            prolong_vco <= '0';
                            current_state <= s_scan;
                        END IF;
                    WHEN s_restart =>
                        -- restart scanning, ensure that the segment waveform generators are properly reset
                        prolong_lsr <= '1';
                        prolong_vco <= '1';
                        IF is_lst_seg_lsr = '0' THEN
                            current_state <= s_prepare;
                        END IF;
                    WHEN s_scan =>
                        -- wait for segment waveform generators to scan voltages
                        IF is_lst_seg_lsr = '1'  AND detect_soliton = '1' THEN
                            time_cnt <= (OTHERS => '0');
                            none_counter <= (OTHERS => '0');
                            soliton_counter <= (OTHERS => '0');
                            MI_counter <= (OTHERS => '0');
                            current_state <= s_detect;
                        END IF;
                    WHEN s_detect =>
                        IF soliton_power >= soliton_threshold_max THEN
                            MI_counter <= MI_counter + x"00000001";
                        ELSIF soliton_power <= soliton_threshold_min THEN
                            none_counter <= none_counter + x"00000001";
                        ELSE
                            soliton_counter <= soliton_counter + x"00000001";
                        END IF;
                        IF time_cnt = detection_time THEN
                            IF MI_counter > soliton_counter AND MI_counter > none_counter THEN
                                -- MI detected
                                MI_detected <= '1';
                                current_state <= s_restart;
                            ELSIF soliton_counter > none_counter THEN
                                -- soliton detected
                                initiate_lsr <= '1';
                                initiate_vco <= '1';
                                prolong_lsr <= '1';
                                prolong_vco <= '1';
                                time_cnt <= (OTHERS => '0');
                                output_voltage_lsr <= vol_lsr_in; -- record the current output of segment waveform generator
                                output_voltage_vco <= vol_vco_in;
                                current_state <= s_coarse;
                            ELSIF vol_lsr_in <= min_vol_lsr THEN
                                -- minimum reached
                                minimum_reached <= '1';
                                current_state <= s_prepare;
                            ELSE 
                                -- nothing special
                                current_state <= s_wait; 
                            END;
                        ELSE
                            time_cnt <= time_cnt + x"00000001";
                        END IF;
                    WHEN s_wait =>
                        -- wait for the next cycle
                        IF is_lst_seg_lsr = '0' THEN
                            current_state <= s_scan;
                        END IF;
                    WHEN s_coarse =>
                        IF time_cnt = coarse_period THEN
                            IF soliton_power_avg > coarse_target THEN
                                output_voltage_lsr <= output_voltage_lsr - x"0001";
                            ELSIF soliton_power_avg < floor THEN
                                soliton_failure <= '1'
                                current_state <= s_prepare;
                            ELSE
                                current_state <= s_fine;
                            END IF;
                            time_cnt <= (OTHERS => '0');
                        ELSE
                            time_cnt <= time_cnt + x"00000001";
                        END IF;
                    WHEN s_fine =>
                        IF time_cnt = fine_period THEN
                            IF soliton_power_avg > fine_target THEN
                                output_voltage_lsr <= output_voltage_lsr - x"0001";
                            ELSIF soliton_power_avg < floor THEN
                                soliton_failure <= '1'
                                current_state <= s_prepare;
                            ELSE
                                stab_counter <= (OTHERS => '0');
                                current_state <= s_stabilize;
                            END IF;
                            time_cnt <= (OTHERS => '0');
                        ELSE
                            time_cnt <= time_cnt + x"00000001";
                        END IF;
                    WHEN s_stabilize =>
                        IF time_cnt = stab_period THEN
                            IF soliton_power_avg < floor THEN
                                soliton_failure <= '1'
                                current_state <= s_prepare;
                            ELSE
                                IF stab_counter < stab_target THEN
                                    stab_counter <= stab_counter + x"0001";
                                    output_voltage_lsr <= output_voltage_lsr + x"0001";
                                ELSE
                                    current_state <= s_longterm;
                                END IF;
                            END IF;
                            time_cnt <= (OTHERS => '0');
                        ELSE
                            time_cnt <= time_cnt + x"00000001";
                        END IF;
                    WHEN s_longterm =>
                        -- longterm stabilization
                    WHEN s_failure =>
                        initiate_lsr <= '1';
                        initiate_vco <= '1';
                        prolong_lsr <= '1';
                        prolong_vco <= '1';
                END CASE;
            END IF;
        END IF;
    END PROCESS;

    -- output
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                vol_lsr_out <= max_vol_lsr + manual_offset;
                vol_vco_out <= x"0000";
            ELSE
                CASE current_state IS
                    WHEN s_idle =>
                        vol_lsr_out <= max_vol_lsr + manual_offset;
                        vol_vco_out <= x"0000";
                    WHEN s_prepare =>
                        vol_lsr_out <= vol_lsr_in + manual_offset;
                        vol_vco_out <= vol_vco_in;
                    WHEN s_restart =>
                        vol_lsr_out <= vol_lsr_in + manual_offset;
                        vol_vco_out <= vol_vco_in;
                    WHEN s_scan =>
                        vol_lsr_out <= vol_lsr_in + manual_offset;
                        vol_vco_out <= vol_vco_in;
                    WHEN s_detect =>
                        vol_lsr_out <= vol_lsr_in + manual_offset;
                        vol_vco_out <= vol_vco_in;
                    WHEN s_coarse =>
                        vol_lsr_out <= output_voltage_lsr + manual_offset;
                        vol_vco_out <= output_voltage_vco;
                    WHEN s_fine =>
                        vol_lsr_out <= output_voltage_lsr + manual_offset;
                        vol_vco_out <= output_voltage_vco;
                    WHEN s_stabilize =>
                        vol_lsr_out <= output_voltage_lsr + manual_offset;
                        vol_vco_out <= output_voltage_vco;
                    WHEN s_longterm =>
                        vol_lsr_out <= output_voltage_lsr + manual_offset;
                        vol_vco_out <= output_voltage_vco;
                    WHEN s_failure =>
                        vol_lsr_out <= max_vol_lsr + manual_offset;
                        vol_vco_out <= x"0000";
                END CASE;
            END IF;
        END IF;
    END PROCESS;
END bhvr;