ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL ref, ref_shift : signed(15 DOWNTO 0);
    SIGNAL I,Q : signed(15 DOWNTO 0);
    SIGNAL MyClk : std_logic;
    SIGNAL phase : signed(15 DOWNTO 0);
    SIGNAL freq : signed(15 DOWNTO 0);

    SIGNAL error : signed(15 DOWNTO 0);

    SIGNAL lock_mode : std_logic_vector(1 DOWNTO 0);

    SIGNAL fast_control : signed(15 DOWNTO 0);
    SIGNAL slow_actual : signed(15 DOWNTO 0);

    SIGNAL enable_auto_match : std_logic;
    SIGNAL initiate_auto_match : std_logic;

    SIGNAL auto_LO_Reset : std_logic := '0';
    SIGNAL auto_fast_PID_Reset : std_logic := '1';
    SIGNAL auto_slow_PID_Reset : std_logic := '1';
    SIGNAL LO_Reset : std_logic;
    SIGNAL fast_PID_Reset : std_logic;
    SIGNAL slow_PID_Reset : std_logic;

    SIGNAL auto_match_freq : signed(15 DOWNTO 0) := x"0000";
    SIGNAL LO_freq : unsigned(15 DOWNTO 0);

    SIGNAL monitorC : signed(15 DOWNTO 0);
    SIGNAL monitorD : signed(15 DOWNTO 0);
BEGIN
    enable_auto_match <= Control0(12);
    initiate_auto_match <= Control0(13);

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF enable_auto_match = '1' THEN
                LO_Reset <= Control0(1);
                fast_PID_Reset <= Control0(10);
                slow_PID_Reset <= Control0(11);
                LO_freq <= unsigned(Control7(31 DOWNTO 16));
            ELSE
                LO_Reset <= auto_LO_Reset;
                fast_PID_Reset <= auto_fast_PID_Reset;
                slow_PID_Reset <= auto_slow_PID_Reset;
                LO_freq <= unsigned(auto_match_freq) + unsigned(Control7(31 DOWNTO 16));
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
        -- try to acquire a faster frequency sweeping speed by actively sweeping the output voltage
        -- find a way to reduce fluctuations when sweeping
        -- figure out why sometimes the locking is unstable

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
                    CASE current_state IS
                        WHEN ready =>
                            IF initiate_auto_match = '0' AND last_initiate = '1' THEN
                                auto_fast_PID_Reset <= '1';
                                auto_slow_PID_Reset <= '1';
                                current_state <= match;
                            END IF;
                            last_initiate <= initiate_auto_match;
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

            K_P => signed(Control12(31 DOWNTO 0)),
            K_I => signed(Control13(31 DOWNTO 0)),
            K_D => signed(Control14(31 DOWNTO 0)),

            limit_I => x"0000200000000000",

            limit_sum => x"3400", -- maximum +- 4MHz

            Reset => PID_Reset,
            Clk => Clk
        );
    END BLOCK auto_match_logic;

    DUT1 : ENTITY WORK.AWG PORT MAP(
        frequency_bias => LO_freq,

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
        Reset => '0'
    );
    DUT4 : ENTITY WORK.atan PORT MAP(
        inputC => I,
        inputS => Q,
        output => phase, -- positive phase angle indicates a negative init phase in input signal
        Clk => Clk
    );
    
    -- this module will be used for auto matching instead of frequency locking
    DUT7 : ENTITY WORK.phase2freq GENERIC MAP(
        gain => 5 -- resolves +- 4.8MHz
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
    
    -- fast PID
    -- PI corner at 30Hz - 6kHz, set default PI corner at 759Hz(16 bit)
    -- PD corner at 200kHz - 2MHz, set default PD corner at 777kHz(6 bit)
    DUT5 : ENTITY WORK.PID PORT MAP(
        actual => error,
        setpoint => x"0000",
        control => fast_control,

        K_P => signed(Control2(31 DOWNTO 0)),
        K_I => signed(Control3(31 DOWNTO 0)),
        K_D => signed(Control4(31 DOWNTO 0)),

        limit_I => x"0001000000000000",

        limit_sum => x"7FFF",

        Reset => fast_PID_Reset,
        Clk => Clk
    );
    OutputA <= fast_control;

    -- slow PID
    -- PI corner at 650mHz(26 bit)
    DUT6 : ENTITY WORK.PID PORT MAP(
        actual => slow_actual,
        setpoint => x"0000",
        control => OutputB,

        K_P => signed(Control8(31 DOWNTO 0)),
        K_I => signed(Control9(31 DOWNTO 0)),
        K_D => signed(Control10(31 DOWNTO 0)),

        limit_I => x"0001000000000000",

        limit_sum => x"7FFF",

        Reset => slow_PID_Reset,
        Clk => Clk
    );
    slow_actual <= error WHEN Control0(6) = '0' ELSE
                    fast_control;

    -- monitor
    monitorC <= phase WHEN Control1(15 DOWNTO 14) = "00" ELSE
                freq WHEN Control1(15 DOWNTO 14) = "01" ELSE
                I WHEN Control1(15 DOWNTO 14) = "10" ELSE
                auto_match_freq;

    monitorD <= phase WHEN Control1(13 DOWNTO 12) = "00" ELSE
                freq WHEN Control1(13 DOWNTO 12) = "01" ELSE
                I WHEN Control1(13 DOWNTO 12) = "10" ELSE
                auto_match_freq;

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            OutputC <= monitorC;
            OutputD <= monitorD;
        END IF;
    END PROCESS;
END bhvr;