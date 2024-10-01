LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

-- potential problem : summing of the 4 products violates the timing constraints
ENTITY multiplier_signed_2stage_piped IS
    GENERIC(
        half_word_length_A : INTEGER := 8;
        half_word_length_B : INTEGER := 8
    );
    PORT(
        A : IN signed(2 * half_word_length_A - 1 DOWNTO 0);
        B : IN signed(2 * half_word_length_B - 1 DOWNTO 0);
        P : OUT signed(2 * half_word_length_A + 2 * half_word_length_B - 1 DOWNTO 0);
        Clk : IN std_logic
    );
END multiplier_signed_2stage_piped;

ARCHITECTURE decom_by_4 OF multiplier_signed_2stage_piped IS
    SIGNAL A_high : signed(half_word_length_A - 1 DOWNTO 0);
    SIGNAL B_high : signed(half_word_length_B - 1 DOWNTO 0);
    SIGNAL A_low : signed(half_word_length_A DOWNTO 0);
    SIGNAL B_low : signed(half_word_length_B DOWNTO 0);
    SIGNAL reg_AhBh : signed(half_word_length_A + half_word_length_B - 1 DOWNTO 0);
    SIGNAL reg_AhBl, reg_AlBh : signed(half_word_length_A + half_word_length_B DOWNTO 0);
    SIGNAL reg_AlBl : signed(half_word_length_A + half_word_length_B + 1 DOWNTO 0);
    SIGNAL AhBh, AhBl, AlBh, AlBl : signed(half_word_length_A + half_word_length_B - 1 DOWNTO 0);
    SIGNAL buf_sum1, buf_sum2 : signed(2 * half_word_length_A + 2 * half_word_length_B - 1 DOWNTO 0);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            AhBh <= reg_AhBh;
            AlBl <= reg_AlBl(half_word_length_A + half_word_length_B - 1 DOWNTO 0);
            AhBl <= reg_AhBl(half_word_length_A + half_word_length_B - 1 DOWNTO 0);
            AlBh <= reg_AlBh(half_word_length_A + half_word_length_B - 1 DOWNTO 0);
        END IF;
    END PROCESS;

    A_high <= A(2 * half_word_length_A - 1 DOWNTO half_word_length_A);
    A_low <= '0' & A(half_word_length_A - 1 DOWNTO 0);
    B_high <= B(2 * half_word_length_B - 1 DOWNTO half_word_length_B);
    B_low <= '0' & B(half_word_length_B - 1 DOWNTO 0);

    reg_AhBh <= A_high * B_high;
    reg_AlBl <= A_low * B_low;
    reg_AhBl <= A_high * B_low;
    reg_AlBh <= A_low * B_high;

    buf_sum1 <= (AhBh & (half_word_length_A + half_word_length_B - 1 DOWNTO 0 => '0'))
                + ((half_word_length_B - 1 DOWNTO 0 => AhBl(half_word_length_A + half_word_length_B - 1)) & AhBl & (half_word_length_A - 1 DOWNTO 0 => '0'));
    buf_sum2 <= ((half_word_length_A - 1 DOWNTO 0 => AlBh(half_word_length_A + half_word_length_B - 1)) & AlBh & (half_word_length_B - 1 DOWNTO 0 => '0'))
                + ((half_word_length_A + half_word_length_B - 1 DOWNTO 0 => '0') & AlBl);
    P <= buf_sum1 + buf_sum2;
END decom_by_4;

ARCHITECTURE decom_by_2 OF multiplier_signed_2stage_piped IS
    -- Assume A is a wide signed but B is not
    SIGNAL A_high : signed(half_word_length_A - 1 DOWNTO 0);
    SIGNAL A_low : signed(half_word_length_A DOWNTO 0);
    SIGNAL reg_AhB : signed(half_word_length_A + 2 * half_word_length_B - 1 DOWNTO 0);
    SIGNAL reg_AlB : signed(half_word_length_A + 2 * half_word_length_B DOWNTO 0);
    SIGNAL AhB, AlB : signed(half_word_length_A + 2 * half_word_length_B - 1 DOWNTO 0);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            AhB <= reg_AhB;
            AlB <= reg_AlB(half_word_length_A + 2 * half_word_length_B - 1 DOWNTO 0);
        END IF;
    END PROCESS;

    A_high <= A(2 * half_word_length_A - 1 DOWNTO half_word_length_A);
    A_low <= '0' & A(half_word_length_A - 1 DOWNTO 0);

    reg_AhB <= A_high * B;
    reg_AlB <= A_low * B;

    P <= (AhB & (half_word_length_A - 1 DOWNTO 0 => '0')) + ((half_word_length_A - 1 DOWNTO 0 => AlB(half_word_length_A + 2 * half_word_length_B - 1)) & AlB);
END decom_by_2;