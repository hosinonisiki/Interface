ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL ref, ref_shift : signed(15 DOWNTO 0);
    SIGNAL I,Q : signed(15 DOWNTO 0);
    SIGNAL MyClk : std_logic;
    SIGNAL phase : signed(15 DOWNTO 0);
    SIGNAL freq : signed(15 DOWNTO 0);

    SIGNAL error : signed(15 DOWNTO 0);

    SIGNAL lock_mode : std_logic;
BEGIN

    -- todo : dynamic PID hardware gain
    DUT1 : ENTITY WORK.AWG PORT MAP(
        frequency_bias => unsigned(Control7(31 DOWNTO 16)),

        set_sign => Control0(2),
        set_x => unsigned(Control5),
        set_y => unsigned(Control6(31 DOWNTO 16)),
        set_slope => unsigned(Control6(15 DOWNTO 0)),
        set_address => unsigned(Control2(7 DOWNTO 4)),
        set => Control0(7),
        segments_enabled => unsigned(Control2(11 DOWNTO 8)),
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
        rate => unsigned(Control2(3 DOWNTO 0)), -- bandpass below 9.8MHz
        MyClk => MyClk
    );
    DUT3 : ENTITY WORK.QI_demodulator PORT MAP(
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
    
    DUT7 : ENTITY WORK.phase2freq PORT MAP(
        phase => phase,
        freq => freq,
      
        Clk => Clk,
        Reset => Reset
    );

    lock_mode <= Control0(6); -- 0: phase lock, 1: frequency lock

    error <= phase WHEN lock_mode = '0' ELSE
                freq;
    
    -- fast PID
    DUT5 : ENTITY WORK.PID GENERIC MAP(
        -- tunable range 32768 times
        -- PI corner at 30Hz - 6kHz, set default PI corner at 759Hz(16 bit)
        -- PD corner at 200kHz - 2MHz, set default PD corner at 777kHz(6 bit)
        gain_P => 8,
        gain_I => -8,
        gain_D => 10
    )PORT MAP(
        actual => error,
        setpoint => x"0000",
        control => OutputA,
        Test => OPEN,

        K_P => signed(Control1(31 DOWNTO 16)),
        K_I => signed(Control1(15 DOWNTO 0)),
        K_D => signed(Control2(31 DOWNTO 16)),

        limit_P => x"6800",
        limit_I => x"6800",
        limit_D => x"6800",

        limit_sum => x"7FFF",

        Reset => Control0(0),
        Clk => Clk
    );
    -- slow PID
    DUT6 : ENTITY WORK.PID GENERIC MAP(
        -- PI corner at 650mHz(26 bit)
        gain_P => 10,
        gain_I => -16,
        gain_D => 0
    )PORT MAP(
        actual => error,
        setpoint => x"0000",
        control => OutputB,
        Test => OPEN,

        K_P => signed(Control3(31 DOWNTO 16)),
        K_I => signed(Control3(15 DOWNTO 0)),
        K_D => signed(Control4(31 DOWNTO 16)),

        limit_P => x"6800",
        limit_I => signed(Control4(15 DOWNTO 0)),
        limit_D => x"6800",

        limit_sum => x"7FFF",

        Reset => Control0(0),
        Clk => Clk
    );

    -- monitor
    OutputC <= phase WHEN Control2(15 DOWNTO 14) = "00" ELSE
                freq WHEN Control2(15 DOWNTO 14) = "01" ELSE
                I WHEN Control2(15 DOWNTO 14) = "10" ELSE
                Q;

    OutputD <= phase WHEN Control2(13 DOWNTO 12) = "00" ELSE
                freq WHEN Control2(13 DOWNTO 12) = "01" ELSE
                I WHEN Control2(13 DOWNTO 12) = "10" ELSE
                Q;
END bhvr;