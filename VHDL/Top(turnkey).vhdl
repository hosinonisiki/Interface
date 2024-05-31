ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL soliton_power : signed(15 DOWNTO 0); -- raw input signal
    SIGNAL input_gain : signed(7 DOWNTO 0); -- 16 refers to 1, 32 refers to 2x gain, etc.
    SIGNAL reg_soliton_power_scaled : signed(23 DOWNTO 0);
    SIGNAL soliton_power_scaled : signed(15 DOWNTO 0);

    SIGNAL scanning_voltage_lsr : signed(15 DOWNTO 0); -- raw output signal
    SIGNAL output_gain_lsr : signed(7 DOWNTO 0); -- 16 refers to 1, 32 refers to 2x gain, etc.
    SIGNAL reg_scanning_voltage_lsr_scaled : signed(23 DOWNTO 0);
    SIGNAL scanning_voltage_lsr_scaled : signed(15 DOWNTO 0);

    SIGNAL scanning_voltage_vco : signed(15 DOWNTO 0);
    SIGNAL output_gain_vco : signed(7 DOWNTO 0);
    SIGNAL reg_scanning_voltage_vco_scaled : signed(23 DOWNTO 0);
    SIGNAL scanning_voltage_vco_scaled : signed(15 DOWNTO 0);

    SIGNAL rst_lsr : std_logic; -- reset signal for the laser
    SIGNAL rst_vco : std_logic; -- reset signal for the VCO

    SIGNAL vol_lsr : unsigned(15 DOWNTO 0); -- voltage output to the laser
    SIGNAL vol_vco : unsigned(15 DOWNTO 0); -- voltage output to the VCO

    SIGNAL set_sign_lsr : std_logic;
    SIGNAL set_x_lsr : unsigned(31 DOWNTO 0);
    SIGNAL set_y_lsr : unsigned(15 DOWNTO 0);
    SIGNAL set_slope_lsr : unsigned(15 DOWNTO 0);
    SIGNAL set_address_lsr : unsigned(3 DOWNTO 0);
    SIGNAL set_lsr : std_logic;

    SIGNAL segments_enabled_lsr : unsigned(3 DOWNTO 0);
    SIGNAL initiate_lsr : std_logic;
    SIGNAL periodic_lsr : std_logic;
    SIGNAL prolong_lsr : std_logic;

    SIGNAL current_segment_lsr : unsigned(3 DOWNTO 0);
    SIGNAL is_last_segment_lsr : std_logic;

    SIGNAL set_sign_vco : std_logic;
    SIGNAL set_x_vco : unsigned(31 DOWNTO 0);
    SIGNAL set_y_vco : unsigned(15 DOWNTO 0);
    SIGNAL set_slope_vco : unsigned(15 DOWNTO 0);
    SIGNAL set_address_vco : unsigned(3 DOWNTO 0);
    SIGNAL set_vco : std_logic;

    SIGNAL segments_enabled_vco : unsigned(3 DOWNTO 0);
    SIGNAL initiate_vco : std_logic;
    SIGNAL periodic_vco : std_logic;
    SIGNAL prolong_vco : std_logic;

    SIGNAL current_segment_vco : unsigned(3 DOWNTO 0);
    
    SIGNAL soliton_power_avg : signed(15 DOWNTO 0);
BEGIN
    -- TODO : add a PID controller

    -- input buffer
    soliton_power <= InputA;
    reg_soliton_power_scaled <= soliton_power * input_gain;
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            soliton_power_scaled <= reg_soliton_power_scaled(19 DOWNTO 4);
        END IF;
    END PROCESS;
    input_gain <= signed(Control14(7 DOWNTO 0));

    -- output buffer
    OutputA <= scanning_voltage_lsr_scaled;
    OutputB <= scanning_voltage_vco_scaled;
    reg_scanning_voltage_lsr_scaled <= scanning_voltage_lsr * output_gain_lsr;
    reg_scanning_voltage_vco_scaled <= scanning_voltage_vco * output_gain_vco;
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            scanning_voltage_lsr_scaled <= reg_scanning_voltage_lsr_scaled(19 DOWNTO 4);
            scanning_voltage_vco_scaled <= reg_scanning_voltage_vco_scaled(19 DOWNTO 4);
        END IF;
    END PROCESS;
    output_gain_lsr <= signed(Control14(15 DOWNTO 8));
    output_gain_vco <= signed(Control14(23 DOWNTO 16));

    -- the io signals are respectively soliton_power_scaled, scanning_voltage_lsr and scanning_voltage_vco, appearing to the internal modules

    DUT1 : ENTITY WORK.turnkey_control PORT MAP(
        soliton_power => soliton_power_scaled,
        soliton_power_avg => soliton_power_avg,

        vol_lsr_in => signed(vol_lsr),
        vol_lsr_out => scanning_voltage_lsr,
        vol_vco_in => signed(vol_vco),
        vol_vco_out => scanning_voltage_vco,

        max_vol_lsr => signed(Control3(31 DOWNTO 16)),
        min_vol_lsr => signed(Control3(15 DOWNTO 0)),
        is_lst_seg_lsr => is_last_segment_lsr,

        soliton_threshold_max => signed(Control6(31 DOWNTO 16)),
        soliton_threshold_min => signed(Control6(15 DOWNTO 0)),
        detection_time => unsigned(Control2(31 DOWNTO 0)),

        approaches => unsigned(Control7(23 DOWNTO 16)),

        coarse_target => signed(Control7(15 DOWNTO 0)),
        fine_target => signed(Control8(31 DOWNTO 16)),

        coarse_period => unsigned(Control8(15 DOWNTO 0)) & x"0000",
        fine_period => unsigned(Control9(31 DOWNTO 16)) & x"0000",
        
        stab_target => signed(Control9(15 DOWNTO 0)),
        stab_period => unsigned(Control10(31 DOWNTO 16)) & x"0000",

        floor => signed(Control10(15 DOWNTO 0)),

        detect_soliton => Control0(1),
        PID_lock => Control0(2),
        immediate_PID => Control0(3),

        initiate_lsr => initiate_lsr,
        prolong_lsr => prolong_lsr,
        initiate_vco => initiate_vco,
        prolong_vco => prolong_vco,

        manual_offset => signed(Control15(31 DOWNTO 16)),

        rst_lsr => rst_lsr,
        rst_vco => rst_vco,

        Clk => Clk,
        Reset => Control0(0)
    );

    -- the AWG module is capable of storing segment waveforms of frequency and generate sine waves accordingly
    -- here we'll just make use of its frequency output as the segment waveform generator

    -- signal to laser
    DUT4 : ENTITY WORK.AWG PORT MAP(
        frequency_bias => unsigned(Control3(31 DOWNTO 16)), -- in the original purpose, this is the default output frequency, in this case corresponding to the idle voltage
        -- parameters for setting the waveform, refer to the AWG module for details
        set_sign => Control0(4),
        set_x => unsigned(Control4(31 DOWNTO 0)),
        set_y => unsigned(Control5(31 DOWNTO 16)),
        set_slope => unsigned(Control5(15 DOWNTO 0)),
        set_address => unsigned(Control1(15 DOWNTO 12)),
        set => Control0(5),

        segments_enabled => unsigned(Control1(11 DOWNTO 8)),
        initiate => initiate_lsr,
        periodic => '0',
        prolong => prolong_lsr,

        amplitude => x"0000",

        control_working => OPEN,
        current_segment => current_segment_lsr,

        outputF => vol_lsr,

        outputC => OPEN,
        outputS => OPEN,

        Reset => rst_lsr, 
        Clk => Clk
    );
    is_last_segment_lsr <= '1' WHEN current_segment_lsr = segments_enabled_lsr + x"F" ELSE '0';

    -- signal to VCO
    DUT5 : ENTITY WORK.AWG PORT MAP(
        frequency_bias => x"0000", -- VCO voltage is 0 by default
        set_sign => Control0(6),
        set_x => unsigned(Control11(31 DOWNTO 0)),
        set_y => unsigned(Control12(31 DOWNTO 16)),
        set_slope => unsigned(Control12(15 DOWNTO 0)),
        set_address => unsigned(Control1(7 DOWNTO 4)),
        set => Control0(7),

        segments_enabled => unsigned(Control1(3 DOWNTO 0)),
        initiate => initiate_vco,
        periodic => '0',
        prolong => prolong_vco,

        amplitude => x"0000",

        control_working => OPEN,
        current_segment => OPEN,

        outputF => vol_vco,

        outputC => OPEN,
        outputS => OPEN,

        Reset => rst_vco, 
        Clk => Clk
    );

    DUT6 : ENTITY WORK.moving_average GENERIC MAP(
        tap => 64,
        logtap => 6
    )PORT MAP(
        input => soliton_power_scaled,
        output => soliton_power_avg,
        Clk => Clk,
        Reset => Control0(0)
    );
END bhvr;