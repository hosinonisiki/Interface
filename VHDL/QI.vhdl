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

ARCHITECTURE bhvr OF QI_demodulator IS
    SIGNAL mixerI : signed(31 DOWNTO 0);
    SIGNAL mixerQ : signed(31 DOWNTO 0);
    SIGNAL bufI1 : signed(15 DOWNTO 0);
    SIGNAL bufQ1 : signed(15 DOWNTO 0);
    SIGNAL bufI2 : signed(15 DOWNTO 0);
    SIGNAL bufQ2 : signed(15 DOWNTO 0);
BEGIN
    -- 两路参考，两路混合，两路滤波
    Process(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            mixerI <= input * ref;
            mixerQ <= input * ref_shift;
            I <= bufI2;
            Q <= bufQ2;
        END IF;
    END PROCESS;
    LPF_I1 : ENTITY WORK.FIR_lowpass(bhvr) GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => mixerI(31 DOWNTO 16),
        output => bufI1,
        Clk => Clk,
        Reset => Reset
    );
    LPF_Q1 : ENTITY WORK.FIR_lowpass(bhvr) GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => mixerQ(31 DOWNTO 16),
        output => bufQ1,
        Clk => Clk,
        Reset => Reset
    );
    LPF_I2 : ENTITY WORK.FIR_lowpass(bhvr) GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => bufI1,
        output => bufI2,
        Clk => Clk,
        Reset => Reset
    );
    LPF_Q2 : ENTITY WORK.FIR_lowpass(bhvr) GENERIC MAP(
        output_length => 16
    )
    PORT MAP(
        input => bufQ1,
        output => bufQ2,
        Clk => Clk,
        Reset => Reset
    );
END bhvr;