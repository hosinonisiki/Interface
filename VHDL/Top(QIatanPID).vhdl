ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL ref, ref_shift : signed(15 DOWNTO 0);
    SIGNAL I,Q : signed(15 DOWNTO 0);
    SIGNAL MyClk : std_logic;
    SIGNAL phase : signed(15 DOWNTO 0);
BEGIN
    DUT1 : ENTITY WORK.AWG PORT MAP(
        frequency_bias => unsigned(Control7(31 DOWNTO 16)),

        LUT_sign => (0 => Control0(2), OTHERS => '0'),
        LUT_x => (0 => unsigned(Control5), OTHERS => x"00000000"),
        LUT_y => (0 => unsigned(Control6(31 DOWNTO 16)), OTHERS => x"0000"),
        LUT_slope => (0 => unsigned(Control6(15 DOWNTO 0)), OTHERS => x"0000"),
        segments_enabled => x"0",
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
        rate => x"8", -- bandpass below 9.8MHz
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
    -- fast PID
    DUT5 : ENTITY WORK.PID GENERIC MAP(
        -- tunable range 32768 times
        -- PI corner at 30Hz - 6kHz, set default PI corner at 759Hz(16 bit)
        -- PD corner at 200kHz - 2MHz, set default PD corner at 777kHz(6 bit)
        gain_P => 4,
        gain_I => -12,
        gain_D => 10
    )PORT MAP(
        actual => phase,
        setpoint => x"0000",
        control => OutputA,
        Test => OPEN,

        K_P => signed(Control1(31 DOWNTO 16)),
        K_I => signed(Control1(15 DOWNTO 0)),
        K_D => signed(Control2(31 DOWNTO 16)),

        limit_P => x"2000",
        limit_I => x"2000",
        limit_D => x"2000",

        Reset => Control0(0),
        Clk => Clk
    );
    -- slow PID
    DUT6 : ENTITY WORK.PID GENERIC MAP(
        -- PI corner at 650mHz(26 bit)
        gain_P => 6,
        gain_I => -20,
        gain_D => 0
    )PORT MAP(
        actual => phase,
        setpoint => x"0000",
        control => OutputB,
        Test => OPEN,

        K_P => signed(Control3(31 DOWNTO 16)),
        K_I => signed(Control3(15 DOWNTO 0)),
        K_D => signed(Control4(31 DOWNTO 16)),

        limit_P => x"2000",
        limit_I => signed(Control4(15 DOWNTO 0)),
        limit_D => x"2000",

        Reset => Control0(0),
        Clk => Clk
    );
END bhvr;