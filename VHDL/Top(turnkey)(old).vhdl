ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL soliton_power_avg_A : signed(15 DOWNTO 0);
    SIGNAL soliton_power_avg_B : signed(15 DOWNTO 0);
    SIGNAL is_longterm : std_logic;
    SIGNAL PID_input : signed(15 DOWNTO 0);
    SIGNAL PID_setpoint : signed(15 DOWNTO 0);
    SIGNAL PID_Reset : std_logic;
BEGIN
    DUT1 : ENTITY WORK.turnkey(bhvr) PORT MAP(
        soliton_power_unscaled => InputA,
        soliton_power_avg_unscaled => soliton_power_avg_A,
        scanning_voltage_scaled => OutputA,

        LUT_period => (unsigned(Control1(31 DOWNTO 16)) & x"00", unsigned(Control1(15 DOWNTO 0)) & x"00", unsigned(Control2(31 DOWNTO 16)) & x"00"),
        hold_period => unsigned(Control2(15 DOWNTO 0)) & x"00",
        max_voltage => signed(Control3(31 DOWNTO 16)),
        min_voltage => signed(Control3(15 DOWNTO 0)),
        step_voltage => signed(Control4(31 DOWNTO 16)),
        LUT_amplitude => (unsigned(Control4(15 DOWNTO 0)), unsigned(Control5(31 DOWNTO 16)), unsigned(Control5(15 DOWNTO 0))),
        soliton_threshold_max => signed(Control6(31 DOWNTO 16)),
        soliton_threshold_min => signed(Control6(15 DOWNTO 0)),

        LUT_slope => (x"0000", x"0000", x"0000"),
        LUT_sign => ('1', '0', '1'),

        attempts => unsigned(Control7(31 DOWNTO 24)),
        approaches => unsigned(Control7(23 DOWNTO 16)),

        coarse_target => signed(Control7(15 DOWNTO 0)),
        fine_target => signed(Control8(31 DOWNTO 16)),

        coarse_period => unsigned(Control8(15 DOWNTO 0)) & x"00",
        fine_period => unsigned(Control9(31 DOWNTO 16)) & x"00",
        
        stab_target => signed(Control9(15 DOWNTO 0)),
        stab_period => unsigned(Control10(31 DOWNTO 16)) & x"00",

        floor => signed(Control10(15 DOWNTO 0)),
         
        mode => Control0(1),

        sweep_period =>  x"00" & unsigned(Control14(31 DOWNTO 16)),

        input_gain => signed(Control14(7 DOWNTO 0)),
        output_gain => signed(Control14(15 DOWNTO 8)),

        manual_offset => signed(Control15(31 DOWNTO 16)),

        is_longterm => is_longterm,

        Clk => Clk,
        Reset => Control0(0)
    );

    DUT2 : ENTITY WORK.PID(nodecay) PORT MAP(
        actual => PID_input,
        setpoint => PID_setpoint,
        control => OutputB,

        K_P => signed(Control11(31 DOWNTO 0)),
        K_I => signed(Control12(31 DOWNTO 0)),
        K_D => signed(Control13(31 DOWNTO 0)),

        limit_I => x"0001000000000000",

        limit_sum => signed(Control15(15 DOWNTO 0)),

        decay_I => x"40000000",

        Reset => PID_Reset,
        Clk => Clk
    );
    PID_input <= soliton_power_avg_B WHEN Control0(3) = '0' ELSE InputB;
    PID_Reset <= Control0(2) OR is_longterm;
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF PID_Reset = '1' THEN
                PID_setpoint <= PID_input;
            END IF;
        END IF;
    END PROCESS;

    DUT3 : ENTITY WORK.moving_average GENERIC MAP(
        tap => 64,
        logtap => 6
    )PORT MAP(
        input => InputA,
        output => soliton_power_avg_A,
        Clk => Clk,
        Reset => Control0(0)
    );

    DUT4 : ENTITY WORK.moving_average GENERIC MAP(
        tap => 64,
        logtap => 6
    )PORT MAP(
        input => InputB,
        output => soliton_power_avg_B,
        Clk => Clk,
        Reset => Control0(0)
    );
END bhvr;