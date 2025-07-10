ARCHITECTURE feedback OF CustomWrapper IS
    SIGNAL PID_Reset : std_logic;

    SIGNAL input : signed(15 DOWNTO 0);

    SIGNAL phase_diff : signed(31 DOWNTO 0);
    SIGNAL phase : signed(31 DOWNTO 0);
    SIGNAL LO : signed(15 DOWNTO 0);

    SIGNAL product : signed(31 DOWNTO 0);
    SIGNAL mixed : signed(15 DOWNTO 0);

    SIGNAL error : signed(15 DOWNTO 0);

    SIGNAL lock_mode : std_logic_vector(1 DOWNTO 0);

    SIGNAL control : signed(15 DOWNTO 0);

    SIGNAL monitor : signed(15 DOWNTO 0);
    SIGNAL monitor_sel : std_logic_vector(3 DOWNTO 0);
BEGIN
    -- Signal assignment
    input <= InputA;
    phase_diff <= signed(Control1(31 DOWNTO 0));
    lock_mode <= Control0(3 DOWNTO 2);
    monitor_sel <= Control0(7 DOWNTO 4);
    PID_Reset <= Control0(0);
    OutputA <= control;
    
    -- Phase accumulation
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                phase <= (OTHERS => '0');
            ELSE
                phase <= phase + phase_diff;
            END IF;
        END IF;
    END PROCESS;

    -- Sin wave generation
    DUT1 : ENTITY WORK.sincos PORT MAP(
        input => phase(31 DOWNTO 16),
        outputC => OPEN,
        outputS => LO,
        Clk => Clk
    );

    -- Mixer
    product <= LO * input;

    -- LPF
    DUT2 : ENTITY  WORK.IIR_4SLA_4th_order GENERIC MAP(
        coefX => (x"0D61CD428E1", x"020F1087D03", x"0507946A096", x"07F32E2636C", x"D96FD3AB572", x"065DB12DB4E", x"FEA4B070709", x"F75CCB45E44", x"34FC61B22B1", x"F3B0A68DB37", x"FB85E26BCD7", x"029EE3638A4", x"DEBB0AAA0CB", x"09134A2B009", x"05FE91AEA06", x"0341DA799DD", x"0AA82B8B31A"),
        coefY => (x"3B2592F80F9", x"ADD6454F49A", x"32D2F9C184C", x"F43087DC461")
    )PORT MAP(
        input => product(31 DOWNTO 16),
        output => mixed,
        Reset => Reset,
        Clk => Clk
    );

    -- Multiplexer
    error <= mixed WHEN lock_mode = "00" ELSE
                input;

    -- fast PID
    -- PI corner at 30Hz - 6kHz, set default PI corner at 759Hz(16 bit)
    -- PD corner at 200kHz - 2MHz, set default PD corner at 777kHz(6 bit)
    DUT5 : ENTITY WORK.PID(optimized) PORT MAP(
        actual => error,
        setpoint => x"0000",
        control => control,

        K_P => signed(Control2(31 DOWNTO 0)),
        K_I => signed(Control3(31 DOWNTO 0)),
        K_D => signed(Control4(31 DOWNTO 0)),

        limit_I => signed(Control5(31 DOWNTO 0)) & x"00000000",

        limit_sum => signed(Control6(15 DOWNTO 0)),

        decay_I => x"40000000",

        Reset => PID_Reset,
        Clk => Clk
    );

    -- monitor
    monitor <= input WHEN monitor_sel = "0000" ELSE
                LO WHEN monitor_sel = "0001" ELSE
                product(31 DOWNTO 16) WHEN monitor_sel = "0010" ELSE
                mixed WHEN monitor_sel = "0011" ELSE
                error WHEN monitor_sel = "0100" ELSE
                control;

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            OutputB <= monitor;
        END IF;
    END PROCESS;
END feedback;