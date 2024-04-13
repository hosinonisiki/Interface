LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;

ENTITY sincos IS
    PORT(
        -- x"8000" refers to exactly +/-180
        SIGNAL input : IN signed(15 DOWNTO 0);
        -- x"7586A5" refers to 1, while x"800001" refers to -1
        SIGNAL outputC : OUT signed(15 DOWNTO 0);
        SIGNAL outputS : OUT signed(15 DOWNTO 0);
        SIGNAL Clk : IN std_logic
    );
END sincos;

ARCHITECTURE bhvr OF sincos IS
    TYPE signed_iter IS ARRAY(0 TO 18) OF signed(23 DOWNTO 0);
    CONSTANT A :signed_iter := (
        x"200000",
        x"12e405",
        x"09fb38",
        x"051112",
        x"028b0d",
        x"0145d8",
        x"00a2f6",
        x"00517c",
        x"0028be",
        x"00145f",
        x"000a30",
        x"000518",
        x"00028c",
        x"000146",
        x"0000a3",
        x"000051",
        x"000029",
        x"000014",
        x"00000a"
    );
    SIGNAL C, S, Z : signed_iter;
    TYPE signed_reg_buf IS ARRAY(0 TO 8) OF signed(23 DOWNTO 0);
    SIGNAL regC, regS, regZ : signed_reg_buf;
    TYPE sgns IS ARRAY(0 TO 18) OF std_logic;
    SIGNAL D, X : sgns;
    TYPE sgns_reg_buf IS ARRAY(0 TO 8) OF std_logic;
    SIGNAL regD, regX : sgns_reg_buf;
    SIGNAL bufZ : signed(15 DOWNTO 0);
    SIGNAL bufZ2 : signed(23 DOWNTO 0);
    SIGNAL bufX : std_logic;
    SIGNAL bufC : signed(15 DOWNTO 0);
    SIGNAL bufS : signed(15 DOWNTO 0);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            bufZ <= input;
            Z(0) <= bufZ2;
            X(0) <= bufX;
            outputC <= bufC;
            outputS <= bufS;
        END IF;
    END PROCESS;
    bufC <= C(18)(23 DOWNTO 8) XOR x"FFFF" WHEN C(18)(7) = '1' AND X(18) = '1' ELSE
            C(18)(23 DOWNTO 8) + x"0001" WHEN C(18)(7) = '1' AND X(18) = '0' ELSE
            (C(18)(23 DOWNTO 8) XOR x"FFFF") + x"0001" WHEN C(18)(7) = '0' AND X(18) = '1' ELSE
            C(18)(23 DOWNTO 8);
    bufS <= S(18)(23 DOWNTO 8) XOR x"FFFF" WHEN S(18)(7) = '1' AND X(18) = '1' ELSE
            S(18)(23 DOWNTO 8) + x"0001" WHEN S(18)(7) = '1' AND X(18) = '0' ELSE
            (S(18)(23 DOWNTO 8) XOR x"FFFF") + x"0001" WHEN S(18)(7) = '0' AND X(18) = '1' ELSE
            S(18)(23 DOWNTO 8);
    bufZ2 <= bufZ + x"8000" & x"00" WHEN bufX = '1' ELSE
                bufZ & x"00";
    bufX <= bufZ(15) XOR bufZ(14);
    D(0) <= Z(0)(23);
    -- x"475E34" = 0.607253 * x"7586A5"
    C(0) <= x"475E34";
    S(0) <= x"475E34" WHEN D(0) = '0' ELSE
            x"B8A1CC";
    gen : FOR i IN 0 TO 17 GENERATE
        reg : IF (i MOD 2 = 1) GENERATE
            regC((i - 1) / 2) <= C(i) - shift_right(S(i), i + 1) WHEN regD((i - 1) / 2) = '0' ELSE
                                    C(i) + shift_right(S(i), i + 1);
            regS((i - 1) / 2) <= S(i) + shift_right(C(i), i + 1) WHEN regD((i - 1) / 2) = '0' ELSE
                                    S(i) - shift_right(C(i), i + 1);
            regD((i - 1) / 2) <= regZ((i - 1) / 2)(23);
            regX((i - 1) / 2) <= X(i);
            regZ((i - 1) / 2) <= Z(i) - A(i) WHEN D(i) = '0' ELSE
                                    Z(i) + A(i);
            PROCESS(Clk)
            BEGIN
                IF rising_edge(Clk) THEN
                    C(i + 1) <= regC((i - 1) / 2);
                    S(i + 1) <= regS((i - 1) / 2);
                    D(i + 1) <= regD((i - 1) / 2);
                    X(i + 1) <= regX((i - 1) / 2);
                    Z(i + 1) <= regZ((i - 1) / 2);
                END IF;
            END PROCESS;
        END GENERATE reg;
        regless : IF (i MOD 2 /= 1) GENERATE
            C(i + 1) <= C(i) - shift_right(S(i), i + 1) WHEN D(i + 1) = '0' ELSE -- C & S requires lookahead to fully make use of 18 iterations
                        C(i) + shift_right(S(i), i + 1);
            S(i + 1) <= S(i) + shift_right(C(i), i + 1) WHEN D(i + 1) = '0' ELSE
                        S(i) - shift_right(C(i), i + 1);
            D(i + 1) <= Z(i + 1)(23);
            X(i + 1) <= X(i);
            Z(i + 1) <= Z(i) - A(i) WHEN D(i) = '0' ELSE
                        Z(i) + A(i);
            END GENERATE regless;
    END GENERATE gen;
END bhvr;