LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY FIR_lowpass IS
    GENERIC(
        input_length : INTEGER := 16;
        output_length : INTEGER := 16
    );
    PORT(
        SIGNAL input : IN signed(input_length - 1 DOWNTO 0);
        SIGNAL output : OUT signed(output_length - 1 DOWNTO 0);
        SIGNAL Clk, Reset : IN std_logic
    );
END FIR_lowpass;

ARCHITECTURE bhvr OF FIR_lowpass IS
    CONSTANT tap : INTEGER := 21;
    TYPE signed_vec_16 IS ARRAY(0 TO tap - 1) OF signed(input_length - 1 DOWNTO 0);
    TYPE signed_vec_24 IS ARRAY(0 TO tap - 1) OF signed(23 DOWNTO 0);
    TYPE signed_vec_40 IS ARRAY(0 TO tap - 1) OF signed(input_length + 23 DOWNTO 0);
    CONSTANT envelope : signed_vec_24 := (
        x"FDA484",
        x"03A979",
        x"016F41",
        x"FA65A8",
        x"FF3833",
        x"08DC03",
        x"0056F1",
        x"F00B86",
        x"FFEA85",
        x"31B452",
        x"4E70D3",
        x"31B452",
        x"FFEA85",
        x"F00B86",
        x"0056F1",
        x"08DC03",
        x"FF3833",
        x"FA65A8",
        x"016F41",
        x"03A979",
        x"FDA484"
    );
    SIGNAL source : signed_vec_16; -- input_length
    SIGNAL mult : signed_vec_40; -- input_length + 24
    SIGNAL image : signed_vec_24 := (OTHERS => x"000000"); -- same as envelope word length
    SIGNAL sum_buf : signed_vec_24 := (OTHERS => x"000000");
    SIGNAL image_buf : signed_vec_24 := (OTHERS => x"000000");
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            source(0) <= input;
            image(0) <= image_buf(0);
            sum_buf(10) <= sum_buf(0) + sum_buf(1);
            sum_buf(11) <= sum_buf(2) + sum_buf(3);
            sum_buf(12) <= sum_buf(4) + sum_buf(5);
            sum_buf(13) <= sum_buf(6) + sum_buf(7);
            sum_buf(14) <= sum_buf(8) + sum_buf(9);
            sum_buf(15) <= image(20);
            output <= sum_buf(20)(23 DOWNTO 24 - output_length);
        END IF;
    END PROCESS;
    mult(0) <= source(0) * envelope(0);
    image_buf(0) <= mult(0)(input_length + 23 DOWNTO 16);
    sum_buf(16) <= sum_buf(10) + sum_buf(11);
    sum_buf(17) <= sum_buf(12) + sum_buf(13);
    sum_buf(18) <= sum_buf(14) + sum_buf(15);
    sum_buf(19) <= sum_buf(16) + sum_buf(17);
    sum_buf(20) <= sum_buf(18) + sum_buf(19);
    gen : FOR i IN 1 TO tap - 1 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                source(i) <= source(i - 1);
                image(i) <= image_buf(i);
            END IF;
        END PROCESS;
        mult(i) <= source(i) * envelope(i);
        image_buf(i) <= mult(i)(input_length + 23 DOWNTO 16);
        sum : IF (i MOD 2 = 1) GENERATE
            sum_buf((i - 1) / 2) <= image(i - 1) + image(i); -- 0 TO 9 USED
        END GENERATE sum;
    END GENERATE gen;
END bhvr;