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
    SIGNAL bufI : signed(23 DOWNTO 0);
    SIGNAL bufQ : signed(23 DOWNTO 0);
BEGIN
    -- 两路参考，两路混合，两路滤波
    Process(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            mixerI <= input * ref;
            mixerQ <= input * ref_shift;
            I <= bufI(23 DOWNTO 8);
            Q <= bufQ(23 DOWNTO 8);
        END IF;
    END PROCESS;
    LPF_I : ENTITY WORK.FIR_lowpass(bhvr) GENERIC MAP(
        output_length => 24
    )
    PORT MAP(
        input => mixerI(31 DOWNTO 16),
        output => bufI,
        Clk => Clk,
        Reset => Reset
    );
    LPF_Q : ENTITY WORK.FIR_lowpass(bhvr) GENERIC MAP(
        output_length => 24
    )
    PORT MAP(
        input => mixerQ(31 DOWNTO 16),
        output => bufQ,
        Clk => Clk,
        Reset => Reset
    );
END bhvr;