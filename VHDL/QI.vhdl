LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY QI_demodulator IS
    PORT(
        SIGNAL input, ref, ref_shift : IN signed(15 DOWNTO 0);
        -- resizing I,Q is required in running
        SIGNAL I,Q : OUT signed(15 DOWNTO 0);
        SIGNAL Clk, Reset : IN std_logic
    );
END QI_demodulator;

ARCHITECTURE older OF QI_demodulator IS
    SIGNAL mixerI : signed(31 DOWNTO 0);
    SIGNAL mixerQ : signed(31 DOWNTO 0);
    SIGNAL bufI1 : signed(15 DOWNTO 0);
    SIGNAL bufQ1 : signed(15 DOWNTO 0);
    SIGNAL regI1 : signed(15 DOWNTO 0);
    SIGNAL regQ1 : signed(15 DOWNTO 0);
    SIGNAL bufI2 : signed(15 DOWNTO 0);
    SIGNAL bufQ2 : signed(15 DOWNTO 0);
    SIGNAL regI2 : signed(15 DOWNTO 0);
    SIGNAL regQ2 : signed(15 DOWNTO 0);
    SIGNAL bufI3 : signed(15 DOWNTO 0);
    SIGNAL bufQ3 : signed(15 DOWNTO 0);
    SIGNAL regI3 : signed(15 DOWNTO 0);
    SIGNAL regQ3 : signed(15 DOWNTO 0);
    SIGNAL regI4 : signed(15 DOWNTO 0);
    SIGNAL regQ4 : signed(15 DOWNTO 0);
BEGIN
    Process(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            mixerI <= input * ref;
            mixerQ <= input * ref_shift;
            I <= regI4;
            Q <= regQ4;
            bufI1 <= regI1;
            bufQ1 <= regQ1;
            bufI2 <= regI2;
            bufQ2 <= regQ2;
            bufI3 <= regI3;
            bufQ3 <= regQ3;
        END IF;
    END PROCESS;
    LPF_I1 : ENTITY WORK.FIR_lowpass GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => mixerI(31 DOWNTO 16),
        output => regI1,
        Clk => Clk,
        Reset => Reset
    );
    LPF_Q1 : ENTITY WORK.FIR_lowpass GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => mixerQ(31 DOWNTO 16),
        output => regQ1,
        Clk => Clk,
        Reset => Reset
    );
    LPF_I2 : ENTITY WORK.FIR_lowpass GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => bufI1,
        output => regI2,
        Clk => Clk,
        Reset => Reset
    );
    LPF_Q2 : ENTITY WORK.FIR_lowpass GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => bufQ1,
        output => regQ2,
        Clk => Clk,
        Reset => Reset
    );
    LPF_I3 : ENTITY WORK.FIR_lowpass GENERIC MAP(
        output_length => 16
    )
    PORT MAP( 
        input => bufI2,
        output => regI3,
        Clk => Clk,
        Reset => Reset
    );
    LPF_Q3 : ENTITY WORK.FIR_lowpass GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => bufQ2,
        output => regQ3,
        Clk => Clk,
        Reset => Reset
    );
    LPF_I4 : ENTITY WORK.FIR_lowpass GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => bufI3,
        output => regI4,
        Clk => Clk,
        Reset => Reset
    );
    LPF_Q4 : ENTITY WORK.FIR_lowpass GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => bufQ3,
        output => regQ4,
        Clk => Clk,
        Reset => Reset
    );
END older;

ARCHITECTURE newer OF QI_demodulator IS
    SIGNAL mixerI : signed(31 DOWNTO 0);
    SIGNAL mixerQ : signed(31 DOWNTO 0);
    SIGNAL bufI2 : signed(15 DOWNTO 0);
    SIGNAL bufQ2 : signed(15 DOWNTO 0);
BEGIN
    Process(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            mixerI <= input * ref;
            mixerQ <= input * ref_shift;
            I <= bufI2;
            Q <= bufQ2;
        END IF;
    END PROCESS;
    LPF_I1 : ENTITY  WORK.IIR_3SLA_4th_order GENERIC MAP(
        coefX => (x"0D61CD428E1", x"020F1087D03", x"0507946A096", x"D577A3C0435", x"03239774DF3", x"FB00CB6A1C2", x"3ABE3B5B723", x"F69BFE4FD0E", x"FEBA40478DB", x"D92F6CF77F2", x"067794595B2", x"03839BA6033", x"0B7F4DAF280"),
        coefY => (x"3C5BCE285C0", x"AA83F3F0C70", x"35DDEADBEE0", x"F3421C74039")
    )PORT MAP(
        input => mixerI(31 DOWNTO 16),
        output => bufI2,
        Reset => Reset,
        Clk => Clk
    );
    LPF_Q1 : ENTITY WORK.IIR_3SLA_4th_order GENERIC MAP(
        coefX => (x"0D61CD428E1", x"020F1087D03", x"0507946A096", x"D577A3C0435", x"03239774DF3", x"FB00CB6A1C2", x"3ABE3B5B723", x"F69BFE4FD0E", x"FEBA40478DB", x"D92F6CF77F2", x"067794595B2", x"03839BA6033", x"0B7F4DAF280"),
        coefY => (x"3C5BCE285C0", x"AA83F3F0C70", x"35DDEADBEE0", x"F3421C74039")
    )PORT MAP(
        input => mixerQ(31 DOWNTO 16),
        output => bufQ2,
        Reset => Reset,
        Clk => Clk
    );
END newer;