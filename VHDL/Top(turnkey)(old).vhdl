ARCHITECTURE bhvr OF CustomWrapper IS
BEGIN
    DUT : ENTITY WORK.turnkey(bhvr) GENERIC MAP(
        tap => 256,
        logtap => 8
    )PORT MAP(
        soliton_power_unscaled => InputA,
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
        
        PID_K_P => signed(Control11(31 DOWNTO 0)),
        PID_K_I => signed(Control12(31 DOWNTO 0)),
        PID_K_D => signed(Control13(31 DOWNTO 0)),
         
        mode => Control0(1),

        sweep_period =>  x"00" & unsigned(Control14(31 DOWNTO 16)),

        PID_lock => Control0(2),

        PID_limit_sum => x"7000",

        input_gain => signed(Control14(7 DOWNTO 0)),
        output_gain => signed(Control14(15 DOWNTO 8)),

        manual_offset => signed(Control15(31 DOWNTO 16)),

        Clk => Clk,
        Reset => Control0(0),

        TestA => OutputB,
        TestB => OutputC
    );
END bhvr;