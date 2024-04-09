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
BEGIN

    -- todo : dynamic PID hardware gain
    DUT1 : ENTITY WORK.AWG PORT MAP(
        frequency_bias => unsigned(Control7(31 DOWNTO 16)),

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

        Reset => Control0(1),
        Clk => Clk
    );
    DUT2 : ENTITY WORK.CDC PORT MAP(
        Clk => Clk,
        rate => unsigned(Control1(3 DOWNTO 0)), -- bandpass below 9.8MHz
        MyClk => MyClk
    );
    DUT3 : ENTITY WORK.QI_demodulator(newer) PORT MAP(
        input => InputA,
        ref => ref,
        ref_shift => ref_shift,
        I => I,
        Q => Q,
        Clk => MyClk,
        Reset => '0'
    );
    DUT4 : ENTITY WORK.atan PORT MAP(
        inputC => I,
        inputS => Q,
        output => phase, -- positive phase angle indicates a negative init phase in input signal
        Clk => Clk
    );
    
    DUT7 : ENTITY WORK.phase2freq(noavg) PORT MAP(
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

        limit_I => x"000100000000",

        limit_sum => x"7FFF",

        Reset => Control0(10),
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

        limit_I => x"000100000000",

        limit_sum => x"7FFF",

        Reset => Control0(11),
        Clk => Clk
    );
    slow_actual <= error WHEN Control0(6) = '0' ELSE
                    fast_control;

    -- monitor
    OutputC <= phase WHEN Control1(15 DOWNTO 14) = "00" ELSE
                freq WHEN Control1(15 DOWNTO 14) = "01" ELSE
                I WHEN Control1(15 DOWNTO 14) = "10" ELSE
                ref;

    OutputD <= phase WHEN Control1(13 DOWNTO 12) = "00" ELSE
                freq WHEN Control1(13 DOWNTO 12) = "01" ELSE
                I WHEN Control1(13 DOWNTO 12) = "10" ELSE
                ref;
END bhvr;