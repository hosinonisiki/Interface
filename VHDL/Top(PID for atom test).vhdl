LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ARCHITECTURE bhvr OF CustomWrapper IS
    SIGNAL fast_control : signed(15 DOWNTO 0);
    SIGNAL slow_control : signed(15 DOWNTO 0);
    SIGNAL fast_Reset : std_logic;
    SIGNAL slow_Reset : std_logic;
    SIGNAL mode : std_logic;
    SIGNAL auto_Reset : std_logic;
    SIGNAL counter : unsigned(15 DOWNTO 0) := (OTHERS => '0');
    SIGNAL counter_limit : unsigned(15 DOWNTO 0);

    SIGNAL InputB_0 : signed(15 DOWNTO 0);
    SIGNAL InputB_1 : signed(15 DOWNTO 0);
BEGIN
    DUT1 : ENTITY WORK.PID(nodecay) PORT MAP(
        actual => InputA,
        setpoint => signed(Control7(31 DOWNTO 16)),
        control => fast_control,

        K_P => signed(Control1(31 DOWNTO 0)),
        K_I => signed(Control2(31 DOWNTO 0)),
        K_D => signed(Control3(31 DOWNTO 0)),

        limit_I => signed(Control8(31 DOWNTO 0)) & x"00000000",

        limit_sum => signed(Control10(31 DOWNTO 16)),

        decay_I => x"40000000",

        Reset => fast_Reset,

        Clk => Clk
    );

    DUT2 : ENTITY WORK.PID(nodecay) PORT MAP(
        actual => fast_control,
        setpoint => signed(Control7(15 DOWNTO 0)),
        control => slow_control,

        K_P => signed(Control4(31 DOWNTO 0)),
        K_I => signed(Control5(31 DOWNTO 0)),
        K_D => signed(Control6(31 DOWNTO 0)),

        limit_I => signed(Control9(31 DOWNTO 0)) & x"00000000",

        limit_sum => signed(Control10(15 DOWNTO 0)),

        decay_I => x"40000000",

        Reset => slow_Reset,

        Clk => Clk
    );

    mode <= Control0(2);
    slow_Reset <= Control0(1);
    counter_limit <= unsigned(Control11(31 DOWNTO 16));
    
    OutputA <= fast_Control;
    OutputB <= InputB + slow_control;

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF counter = counter_limit THEN
                counter <= (OTHERS => '0');
                InputB_1 <= InputB_0;
                InputB_0 <= InputB;
            ELSE
                counter <= counter + 1;
            END IF;
            IF mode = '0' THEN
                fast_Reset <= Control0(0);
                auto_Reset <= '1';
            END IF;
            IF mode = '1' THEN
                fast_Reset <= auto_Reset;
                IF InputB = InputB_0 AND InputB_0 = InputB_1 THEN
                    auto_Reset <= '0';
                END IF;
            END IF;
        END IF;
    END PROCESS;
END bhvr;