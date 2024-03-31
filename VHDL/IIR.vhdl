LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

PACKAGE MyPak_IIR IS
    TYPE signed_vec_20 IS ARRAY(NATURAL RANGE <>) OF signed(19 DOWNTO 0);
    TYPE signed_vec_24 IS ARRAY(NATURAL RANGE <>) OF signed(23 DOWNTO 0);
    TYPE signed_vec_36 IS ARRAY(NATURAL RANGE <>) OF signed(35 DOWNTO 0);
    TYPE signed_vec_44 IS ARRAY(NATURAL RANGE <>) OF signed(43 DOWNTO 0);
END MyPak_IIR;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

USE WORK.MyPak_IIR.ALL;

-- todo : implement 3SLA
ENTITY IIR_3SLA_4th_order IS
    GENERIC(
        -- word length of IO is 16
        -- internal word length is 20
        -- y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] + b3*x[n-3] + b4*x[n-4]
        --      + a1*y[n-1] + a2*y[n-2] + a3*y[n-3] + a4*y[n-4]
        -- y[n] actually depends on x[n] ~ x[n-6] and y[n-3] ~ y[n-6], cuz a 2 clocks delay is introduced by the multipliers
        -- for how to derive the coefficients, refer to my diagram on draw.io
        coefX : signed_vec_20(0 TO 6); -- ranges from -1 to 1, setting 2 ** 19 as 1
        coefY : signed_vec_20(0 TO 3) -- ranges from -64 to 64, setting 2 ** 13 as 1
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
    SIGNAL Y : signed(23 DOWNTO 0);
    SIGNAL result : signed(23 DOWNTO 0);

    SIGNAL productX : signed_vec_20(0 TO 6);
    SIGNAL reg_productX : signed_vec_36(0 TO 6);
    -- suppose no more than 16 products are summed up
    SIGNAL sumX : signed_vec_20(0 TO 6);
    SIGNAL reg_sumX : signed_vec_20(0 TO 6);

    SIGNAL productY : signed_vec_24(0 TO 3);
    SIGNAL reg_productY : signed_vec_44(0 TO 3);
    SIGNAL sumY : signed_vec_24(0 TO 3);
    SIGNAL reg_sumY : signed_vec_24(0 TO 3);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            X <= input;
            Y <= result;
            sumX(6) <= reg_sumX(6);
            sumY(3) <= reg_sumY(3);

            output <= result(23 DOWNTO 8);
        END IF;
    END PROCESS;

    Xend : FOR i IN 0 TO 6 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                productX(i) <= ((3 DOWNTO 0 => reg_productX(i)(35)) & reg_productX(i)(35 DOWNTO 20));
            END IF;
        END PROCESS;
        reg_productX(i) <= coefX(i) * X WHEN Reset = '0' ELSE (OTHERS => '0');
        Xsum : IF i /= 6 GENERATE
            PROCESS(Clk)
            BEGIN
                IF rising_edge(Clk) THEN
                    sumX(i) <= reg_sumX(i);
                END IF;
            END PROCESS;
            reg_sumX(i) <= sumX(i + 1) + productX(i);
        END GENERATE Xsum;
    END GENERATE Xend;
    reg_sumX(6) <= productX(6) WHEN Reset = '0' ELSE (OTHERS => '0');

    Yend : FOR i IN 0 TO 3 GENERATE
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                productY(i) <= reg_productY(i)(43) & reg_productY(i)(36 DOWNTO 14);
            END IF;
        END PROCESS;
        reg_productY(i) <= coefY(i) * Y WHEN Reset = '0' ELSE (OTHERS => '0');
        Ysum : IF i /= 3 GENERATE
            PROCESS(Clk)
            BEGIN
                IF rising_edge(Clk) THEN
                    sumY(i) <= reg_sumY(i);
                END IF;
            END PROCESS;
            reg_sumY(i) <= sumY(i + 1) + productY(i);
        END GENERATE Ysum;
    END GENERATE Yend;
    reg_sumY(3) <= productY(3) WHEN Reset = '0' ELSE (OTHERS => '0');

    result <= ((3 DOWNTO 0 => sumX(0)(19)) & sumX(0)) + sumY(0) WHEN Reset = '0' ELSE (OTHERS => '0');
END bhvr;