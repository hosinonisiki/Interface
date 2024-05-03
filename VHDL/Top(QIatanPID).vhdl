ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL ref, ref_shift : signed(15 DOWNTO 0);
    SIGNAL I,Q : signed(15 DOWNTO 0);
    SIGNAL phase : signed(15 DOWNTO 0);
    SIGNAL freq : signed(15 DOWNTO 0);

    SIGNAL error : signed(15 DOWNTO 0);

    SIGNAL lock_mode : std_logic_vector(1 DOWNTO 0);

    SIGNAL fast_actual : signed(15 DOWNTO 0);
    SIGNAL fast_control : signed(15 DOWNTO 0);
    SIGNAL slow_actual : signed(15 DOWNTO 0);
    SIGNAL slow_control : signed(15 DOWNTO 0);

    SIGNAL enable_auto_match : std_logic;
    SIGNAL initiate_auto_match : std_logic;

    SIGNAL auto_LO_Reset : std_logic := '0';
    SIGNAL auto_fast_PID_Reset : std_logic := '1';
    SIGNAL auto_slow_PID_Reset : std_logic := '1';
    SIGNAL LO_Reset : std_logic;
    SIGNAL fast_PID_Reset : std_logic;
    SIGNAL slow_PID_Reset : std_logic;

    SIGNAL auto_match_freq : signed(15 DOWNTO 0) := x"0000";
    SIGNAL LO_freq_bias : unsigned(15 DOWNTO 0);

    SIGNAL LO_freq : unsigned(15 DOWNTO 0);
    SIGNAL LO_control_working : std_logic;

    SIGNAL unwrapped : signed(17 DOWNTO 0);
    SIGNAL clamped : signed(15 DOWNTO 0);
    
    SIGNAL enable_compensation : std_logic := '1';
    SIGNAL LO_compensation : signed(15 DOWNTO 0);
    SIGNAL reg_LO_compensation : signed(31 DOWNTO 0);

    SIGNAL monitorC : signed(15 DOWNTO 0);
    SIGNAL monitorD : signed(15 DOWNTO 0);

    SIGNAL TestA : signed(15 DOWNTO 0);
    SIGNAL TestB : signed(15 DOWNTO 0);
    SIGNAL TestC : signed(15 DOWNTO 0);
    SIGNAL TestD : signed(15 DOWNTO 0);
BEGIN
    -- try to acquire a faster frequency sweeping speed by using more complicated strategies instead of pure PID
    -- dynamic PID coefficients

    enable_auto_match <= Control0(12);
    initiate_auto_match <= Control0(13);

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF enable_auto_match = '1' THEN
                LO_Reset <= Control0(1);
                fast_PID_Reset <= Control0(10);
                slow_PID_Reset <= Control0(11);
                LO_freq_bias <= unsigned(Control7(31 DOWNTO 16));
            ELSE
                LO_Reset <= auto_LO_Reset;
                fast_PID_Reset <= auto_fast_PID_Reset;
                slow_PID_Reset <= auto_slow_PID_Reset;
                LO_freq_bias <= unsigned(auto_match_freq) + unsigned(Control7(31 DOWNTO 16));
            END IF;
        END IF;
    END PROCESS;

    auto_match_logic : BLOCK
        TYPE state IS (ready, match, hold);
        SIGNAL current_state : state := ready;

        SIGNAL last_initiate : std_logic := '0';

        SIGNAL auto_match_freq_bias : signed(15 DOWNTO 0);
        SIGNAL auto_match_freq_control : signed(15 DOWNTO 0);
        SIGNAL PID_Reset : std_logic := '1';

        SIGNAL frequency_match_threshold : signed(15 DOWNTO 0);
        SIGNAL frequency_lock_threshold : signed(15 DOWNTO 0);
    BEGIN

        frequency_match_threshold <= signed(Control11(31 DOWNTO 16));
        frequency_lock_threshold <= signed(Control11(15 DOWNTO 0));

        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                IF enable_auto_match = '1' THEN
                    --initialization
                    current_state <= ready;
                    last_initiate <= '0';
                    PID_Reset <= '1';
                    auto_match_freq_bias <= x"0000";

                    auto_LO_Reset <= '0';
                    auto_fast_PID_Reset <= '1';
                    auto_slow_PID_Reset <= '1';
                    auto_match_freq <= x"0000";
                ELSE
                    last_initiate <= initiate_auto_match;
                    CASE current_state IS
                        WHEN ready =>
                            IF initiate_auto_match = '0' AND last_initiate = '1' THEN
                                auto_fast_PID_Reset <= '1';
                                auto_slow_PID_Reset <= '1';
                                current_state <= match;
                            END IF;
                        WHEN match =>
                            PID_Reset <= '0';
                            auto_match_freq <= auto_match_freq_control + auto_match_freq_bias;
                            IF freq < frequency_match_threshold and freq > -frequency_match_threshold THEN -- x0110 around 10kHz
                                current_state <= hold;
                            END IF;
                        WHEN hold =>
                            PID_Reset <= '1';
                            auto_match_freq_bias <= auto_match_freq;
                            auto_fast_PID_Reset <= '0';
                            IF freq < frequency_lock_threshold and freq > -frequency_lock_threshold THEN -- x0003 around 100Hz
                                auto_slow_PID_Reset <= '0';
                                current_state <= ready;
                            END IF;
                    END CASE;
                END IF;
            END IF;
        END PROCESS;

        frequency_match : ENTITY WORK.PID PORT MAP(
            actual => freq,
            setpoint => x"0000",
            control => auto_match_freq_control,

            K_P => x"FFFFC000",
            K_I => x"FFFFE000",
            K_D => x"00000000",

            limit_I => x"0000200000000000",

            limit_sum => x"3400", -- maximum +- 4MHz

            decay_I => x"40000000",

            Reset => PID_Reset,
            Clk => Clk
        );
    END BLOCK auto_match_logic;

    DUT1 : ENTITY WORK.AWG PORT MAP(
        frequency_bias => LO_freq_bias,

        set_sign => Control0(2),
        set_x => unsigned(Control5),
        set_y => unsigned(Control6(31 DOWNTO 16)),
        set_slope => unsigned(Control6(15 DOWNTO 0)),
        set_address => unsigned(Control1(7 DOWNTO 4)),
        set => Control0(7),
        segments_enabled => unsigned(Control1(11 DOWNTO 8)),
        initiate => Control0(3),
        periodic => Control0(4),
        prolong => Control0(5),

        amplitude => signed(Control7(15 DOWNTO 0)),

        control_working => LO_control_working,

        outputF => LO_freq,

        outputC => ref,
        outputS => ref_shift,

        Reset => LO_Reset,
        Clk => Clk
    );
    DUT3 : ENTITY WORK.QI_demodulator(newer) PORT MAP(
        input => InputA,
        ref => ref,
        ref_shift => ref_shift,
        I => I,
        Q => Q,
        Clk => Clk,
        Reset => '0',

        TestA => TestA,
        TestB => TestB,
        TestC => TestC
    );
    DUT4 : ENTITY WORK.atan PORT MAP(
        inputC => I,
        inputS => Q,
        output => phase, -- positive phase angle indicates a negative init phase in input signal
        Clk => Clk
    );
    
    -- this module will be used for auto matching instead of frequency locking
    DUT7 : ENTITY WORK.phase2freq(bhvr) GENERIC MAP(
        tap => 256,
        logtap => 8,
        gain => 4 -- resolves +- 4.8MHz
    )PORT MAP(
        phase => phase,
        freq => freq,
      
        Clk => Clk,
        Reset => Reset
    );

    lock_mode <= Control0(9 DOWNTO 8); -- 0: phase lock, 1: frequency lock, 2: mixed signal lock

    error <= phase WHEN lock_mode = "00" ELSE
                freq WHEN lock_mode = "01" ELSE
                I WHEN lock_mode = "10" ELSE
                Q;
    
    DUT8 : ENTITY WORK.unwrap GENERIC MAP(
        unwrapped_word_length => 18
    )PORT MAP(
        input => phase,
        unwrapped => unwrapped,
        clamped => clamped,
        Clk => Clk,
        Reset => LO_control_working
    );

    -- fast PID
    -- PI corner at 30Hz - 6kHz, set default PI corner at 759Hz(16 bit)
    -- PD corner at 200kHz - 2MHz, set default PD corner at 777kHz(6 bit)
    DUT5 : ENTITY WORK.PID(bhvr) PORT MAP(
        actual => fast_actual,
        setpoint => x"0000",
        control => fast_control,

        K_P => signed(Control2(31 DOWNTO 0)),
        K_I => signed(Control3(31 DOWNTO 0)),
        K_D => signed(Control4(31 DOWNTO 0)),

        limit_I => x"0001000000000000",

        limit_sum => x"7FFF",

        decay_I => x"40000000",

        Reset => fast_PID_Reset,
        Clk => Clk
    );
    OutputA <= fast_control;
    fast_actual <= error WHEN Control0(15) = '1' ELSE
                    clamped;

    -- slow PID
    -- PI corner at 650mHz(26 bit)
    DUT6 : ENTITY WORK.PID(bhvr) PORT MAP(
        actual => slow_actual,
        setpoint => x"0000",
        control => slow_control,

        K_P => signed(Control8(31 DOWNTO 0)),
        K_I => signed(Control9(31 DOWNTO 0)),
        K_D => signed(Control10(31 DOWNTO 0)),

        limit_I => x"0001000000000000",

        limit_sum => x"7FFF",

        decay_I => signed(Control15(31 DOWNTO 0)),

        Reset => slow_PID_Reset,
        Clk => Clk
    );
    slow_actual <= error WHEN Control0(6) = '0' ELSE
                    fast_control;
    enable_compensation <= Control0(14);
    reg_LO_compensation <= signed(LO_freq - LO_freq_bias) * signed(Control12(31 DOWNTO 16));
    OutputB <= slow_control + LO_compensation WHEN enable_compensation = '0' ELSE
               slow_control;
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            LO_compensation <= reg_LO_compensation(23 DOWNTO 8);
        END IF;
    END PROCESS;

    -- monitor
    monitorC <= phase WHEN Control1(15 DOWNTO 12) = "0000" ELSE
                freq WHEN Control1(15 DOWNTO 12) = "0001" ELSE
                I WHEN Control1(15 DOWNTO 12) = "0010" ELSE
                Q WHEN Control1(15 DOWNTO 12) = "0011" ELSE
                error WHEN Control1(15 DOWNTO 12) = "0100" ELSE
                ref WHEN Control1(15 DOWNTO 12) = "0101" ELSE
                ref_shift WHEN Control1(15 DOWNTO 12) = "0110" ELSE
                auto_match_freq WHEN Control1(15 DOWNTO 12) = "0111" ELSE
                TestA WHEN Control1(15 DOWNTO 12) = "1000" ELSE
                TestB WHEN Control1(15 DOWNTO 12) = "1001" ELSE
                TestC WHEN Control1(15 DOWNTO 12) = "1010" ELSE
                TestD WHEN Control1(15 DOWNTO 12) = "1011" ELSE
                signed(LO_freq) WHEN Control1(15 DOWNTO 12) = "1100" ELSE
                signed(LO_freq - LO_freq_bias) WHEN Control1(15 DOWNTO 12) = "1101" ELSE
                unwrapped(17 DOWNTO 2) WHEN Control1(15 DOWNTO 12) = "1110" ELSE
                clamped;


    monitorD <= phase WHEN Control1(15 DOWNTO 12) = "0000" ELSE
                freq WHEN Control1(15 DOWNTO 12) = "0001" ELSE
                I WHEN Control1(15 DOWNTO 12) = "0010" ELSE
                Q WHEN Control1(15 DOWNTO 12) = "0011" ELSE
                error WHEN Control1(15 DOWNTO 12) = "0100" ELSE
                ref WHEN Control1(15 DOWNTO 12) = "0101" ELSE
                ref_shift WHEN Control1(15 DOWNTO 12) = "0110" ELSE
                auto_match_freq WHEN Control1(15 DOWNTO 12) = "0111" ELSE
                TestA WHEN Control1(15 DOWNTO 12) = "1000" ELSE
                TestB WHEN Control1(15 DOWNTO 12) = "1001" ELSE
                TestC WHEN Control1(15 DOWNTO 12) = "1010" ELSE
                TestD WHEN Control1(15 DOWNTO 12) = "1011" ELSE
                signed(LO_freq) WHEN Control1(15 DOWNTO 12) = "1100" ELSE
                signed(LO_freq - LO_freq_bias) WHEN Control1(15 DOWNTO 12) = "1101" ELSE
                unwrapped(17 DOWNTO 2) WHEN Control1(15 DOWNTO 12) = "1110" ELSE
                clamped;

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            OutputC <= monitorC;
            OutputD <= monitorD;
        END IF;
    END PROCESS;
END bhvr;