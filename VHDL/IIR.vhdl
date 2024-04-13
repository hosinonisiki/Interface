LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

PACKAGE MyPak_IIR IS
    TYPE signed_vec_16 IS ARRAY(NATURAL RANGE <>) OF signed(15 DOWNTO 0);
    TYPE signed_vec_44 IS ARRAY(NATURAL RANGE <>) OF signed(43 DOWNTO 0);
    TYPE signed_vec_48 IS ARRAY(NATURAL RANGE <>) OF signed(47 DOWNTO 0);
    TYPE signed_vec_60 IS ARRAY(NATURAL RANGE <>) OF signed(59 DOWNTO 0);
    TYPE signed_vec_88 IS ARRAY(NATURAL RANGE <>) OF signed(87 DOWNTO 0);
END MyPak_IIR;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

USE WORK.MyPak_IIR.ALL;

ENTITY IIR_3SLA_4th_order IS
    GENERIC(
        -- word length of IO is 16
        -- internal word length is 44/48
        -- y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] + b3*x[n-3] + b4*x[n-4]
        --      + a1*y[n-1] + a2*y[n-2] + a3*y[n-3] + a4*y[n-4]
        -- y[n] actually depends on x[n] ~ x[n-12/16] and y[n-3/4] ~ y[n-12/16]
        -- coefficients derived elsewhere
        coefX : signed_vec_44(0 TO 12); -- ranges from -1 to 1, setting 2 ** 19 as 1
        coefY : signed_vec_44(0 TO 3) -- ranges from -8 to 8, setting 2 ** 16 as 1
    );
    PORT(
        input : IN signed(15 DOWNTO 0);
        output : OUT signed(15 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END IIR_3SLA_4th_order;

ARCHITECTURE bhvr OF IIR_3SLA_4th_order IS
    SIGNAL X : signed(15 DOWNTO 0);
    SIGNAL bufX : signed(31 DOWNTO 0);
    SIGNAL Y : signed(43 DOWNTO 0);
    SIGNAL result : signed(43 DOWNTO 0);

    SIGNAL productX : signed_vec_44(0 TO 12);
    SIGNAL reg_productX : signed_vec_60(0 TO 12);
    -- suppose no more than 16 products are summed up
    SIGNAL sumX : signed_vec_44(0 TO 12);
    SIGNAL reg_sumX : signed_vec_44(0 TO 12);

    SIGNAL productY : signed_vec_48(0 TO 3);
    SIGNAL reg_productY : signed_vec_88(0 TO 3);
    SIGNAL sumY : signed_vec_48(0 TO 9);
    SIGNAL reg_sumY : signed_vec_48(0 TO 9);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            bufX <= input * x"7B96";
            X <= bufX(31) & bufX(29 DOWNTO 15);
            Y <= result;
            output <= result(43 DOWNTO 28) + ((14 DOWNTO 0 => '0') & result(27));
        END IF;
    END PROCESS;

    Xend : FOR i IN 0 TO 12 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                productX(i) <= ((8 DOWNTO 0 => reg_productX(i)(59)) & reg_productX(i)(59 DOWNTO 25)) + ((42 DOWNTO 0 => '0') & reg_productX(i)(24));
                sumX(i) <= reg_sumX(i);
            END IF;
        END PROCESS;
        reg_productX(i) <= coefX(i) * X WHEN Reset = '0' ELSE (OTHERS => '0');
        Xsum : IF i /= 12 GENERATE
            reg_sumX(i) <= sumX(i + 1) + productX(i);
        END GENERATE Xsum;
    END GENERATE Xend;
    reg_sumX(12) <= productX(12) WHEN Reset = '0' ELSE (OTHERS => '0');

    Yend : FOR i IN 0 TO 3 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                productY(i) <= reg_productY(i)(87 DOWNTO 40) + ((46 DOWNTO 0 => '0') & reg_productY(i)(39));
            END IF;
        END PROCESS;
        reg_productY(i) <= coefY(i) * Y WHEN Reset = '0' ELSE (OTHERS => '0');
        Ysum : IF i /= 3 GENERATE
            PROCESS(Clk)
            BEGIN
                IF rising_edge(Clk) THEN
                    sumY(i * 3) <= reg_sumY(i * 3);
                    sumY(i * 3 + 1) <= reg_sumY(i * 3 + 1);
                    sumY(i * 3 + 2) <= reg_sumY(i * 3 + 2);
                END IF;
            END PROCESS;
            reg_sumY(i * 3) <= sumY(i * 3 + 1) + productY(i);
            reg_sumY(i * 3 + 1) <= sumY(i * 3 + 2);
            reg_sumY(i * 3 + 2) <= sumY(i * 3 + 3);
        END GENERATE Ysum;
    END GENERATE Yend;
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            sumY(9) <= reg_sumY(9);
        END IF;
    END PROCESS;
    reg_sumY(9) <= productY(3) WHEN Reset = '0' ELSE (OTHERS => '0');

    result <= sumX(0) + (sumY(0)(47) & sumY(0)(42 DOWNTO 0))  WHEN Reset = '0' ELSE (OTHERS => '0');
END bhvr;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

USE WORK.MyPak_IIR.ALL;

ENTITY IIR_4SLA_4th_order IS
    GENERIC(
        coefX : signed_vec_44(0 TO 16);
        coefY : signed_vec_44(0 TO 3)
    );
    PORT(
        input : IN signed(15 DOWNTO 0);
        output : OUT signed(15 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END IIR_4SLA_4th_order;

ARCHITECTURE bhvr OF IIR_4SLA_4th_order IS
    SIGNAL X : signed(15 DOWNTO 0);
    SIGNAL bufX : signed(31 DOWNTO 0);
    SIGNAL Y : signed(43 DOWNTO 0);
    SIGNAL result : signed(43 DOWNTO 0);

    SIGNAL productX : signed_vec_44(0 TO 16);
    SIGNAL reg_productX : signed_vec_60(0 TO 16);
    SIGNAL mult_resultX : signed_vec_60(0 TO 16);
    -- suppose no more than 16 products are summed up
    SIGNAL sumX : signed_vec_44(0 TO 16);
    SIGNAL reg_sumX : signed_vec_44(0 TO 16);

    SIGNAL productY : signed_vec_48(0 TO 3);
    SIGNAL reg_productY : signed_vec_88(0 TO 3);
    SIGNAL mult_resultY : signed_vec_88(0 TO 3);
    SIGNAL sumY : signed_vec_48(0 TO 12);
    SIGNAL reg_sumY : signed_vec_48(0 TO 12);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            bufX <= input * x"7B96";
            X <= bufX(31) & bufX(29 DOWNTO 15);
            Y <= result;
            output <= result(43 DOWNTO 28) + ((14 DOWNTO 0 => '0') & result(27));
        END IF;
    END PROCESS;

    Xend : FOR i IN 0 TO 16 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                productX(i) <= ((8 DOWNTO 0 => reg_productX(i)(59)) & reg_productX(i)(59 DOWNTO 25)) + ((42 DOWNTO 0 => '0') & reg_productX(i)(24));
                sumX(i) <= reg_sumX(i);
            END IF;
        END PROCESS;
        piped_multiplierX : ENTITY WORK.multiplier_signed_2stage_piped GENERIC MAP(
            half_word_length_A => 22,
            half_word_length_B => 8
        )PORT MAP(
            A => coefX(i),
            B => X,
            P => mult_resultX(i),
            Clk => Clk
        );
        reg_productX(i) <= mult_resultX(i) WHEN Reset = '0' ELSE (OTHERS => '0');
        Xsum : IF i /= 16 GENERATE
            reg_sumX(i) <= sumX(i + 1) + productX(i);
        END GENERATE Xsum;
    END GENERATE Xend;
    reg_sumX(16) <= productX(16) WHEN Reset = '0' ELSE (OTHERS => '0');

    Yend : FOR i IN 0 TO 3 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                productY(i) <= reg_productY(i)(87 DOWNTO 40) + ((46 DOWNTO 0 => '0') & reg_productY(i)(39));
            END IF;
        END PROCESS;
        piped_multiplierY : ENTITY WORK.multiplier_signed_2stage_piped GENERIC MAP(
            half_word_length_A => 22,
            half_word_length_B => 22
        )PORT MAP(
            A => coefY(i),
            B => Y,
            P => mult_resultY(i),
            Clk => Clk
        );
        reg_productY(i) <= mult_resultY(i) WHEN Reset = '0' ELSE (OTHERS => '0');
        Ysum : IF i /= 3 GENERATE
            PROCESS(Clk)
            BEGIN
                IF rising_edge(Clk) THEN
                    sumY(i * 4) <= reg_sumY(i * 4);
                    sumY(i * 4 + 1) <= reg_sumY(i * 4 + 1);
                    sumY(i * 4 + 2) <= reg_sumY(i * 4 + 2);
                    sumY(i * 4 + 3) <= reg_sumY(i * 4 + 3);
                END IF;
            END PROCESS;
            reg_sumY(i * 4) <= sumY(i * 4 + 1) + productY(i);
            reg_sumY(i * 4 + 1) <= sumY(i * 4 + 2);
            reg_sumY(i * 4 + 2) <= sumY(i * 4 + 3);
            reg_sumY(i * 4 + 3) <= sumY(i * 4 + 4);
        END GENERATE Ysum;
    END GENERATE Yend;
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            sumY(12) <= reg_sumY(12);
        END IF;
    END PROCESS;
    reg_sumY(12) <= productY(3) WHEN Reset = '0' ELSE (OTHERS => '0');

    result <= sumX(0) + (sumY(0)(47) & sumY(0)(42 DOWNTO 0))  WHEN Reset = '0' ELSE (OTHERS => '0');
END bhvr;