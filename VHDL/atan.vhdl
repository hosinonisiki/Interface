LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.numeric_std.ALL;

ENTITY atan IS
    PORT(
        -- only the ratio matters
        SIGNAL inputC : IN signed(15 DOWNTO 0);
        SIGNAL inputS : IN signed(15 DOWNTO 0);
        -- x"8000" refers to exactly +/-180
        SIGNAL output : OUT signed(15 DOWNTO 0);
        SIGNAL Clk : IN std_logic
    );
END atan;

ARCHITECTURE pipe_by_2 OF atan IS
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
    SIGNAL D : sgns;
    SIGNAL X : sgns;
    TYPE sgns_reg_buf IS ARRAY(0 TO 8) OF std_logic;
    SIGNAL regD : sgns_reg_buf;
    SIGNAL regX : sgns_reg_buf;
    SIGNAL bufC : signed(31 DOWNTO 0);
    SIGNAL bufS : signed(31 DOWNTO 0);
    SIGNAL bufC2 : signed(23 DOWNTO 0);
    SIGNAL bufS2 : signed(23 DOWNTO 0);
    SIGNAL bufX : std_logic;
    SIGNAL bufO : signed(15 DOWNTO 0);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            -- x"7FFF" * x"6DED" = x"36F61213"
            bufC <= inputC * x"6DED";
            bufS <= inputS * x"6DED";
            C(0) <= bufC2;
            S(0) <= bufS2;
            X(0) <= bufX;
            output <= bufO;
        END IF;
    END PROCESS;
    bufO <= Z(18)(23 DOWNTO 8) + x"8001" WHEN Z(18)(7) = '1' AND X(18) = '1' ELSE
                        Z(18)(23 DOWNTO 8) + x"0001" WHEN Z(18)(7) = '1' AND X(18) = '0' ELSE
                        Z(18)(23 DOWNTO 8) + x"8000" WHEN Z(18)(7) = '0' AND X(18) = '1' ELSE
                        Z(18)(23 DOWNTO 8);
    bufC2 <= x"36F612" WHEN bufC(31 DOWNTO 8) = x"000000" AND bufS(31 DOWNTO 8) = x"000000" ELSE
            (bufC(31 DOWNTO 8) XOR x"FFFFFF") + x"000001" WHEN bufX = '1' ELSE
            bufC(31 DOWNTO 8);
    bufS2 <= (bufS(31 DOWNTO 8) XOR x"FFFFFF") + x"000001" WHEN bufX = '1' ELSE
            bufS(31 DOWNTO 8);
    bufX <= bufC(31);
    D(0) <= S(0)(23);
    Z(0) <= - A(0) WHEN D(0) = '1' ELSE
            A(0);
    gen : FOR i IN 0 TO 17 GENERATE
        reg : IF (i MOD 2 = 1) GENERATE
            regC((i - 1) / 2) <= C(i) - shift_right(S(i), i) WHEN D(i) = '1' ELSE
                                    C(i) + shift_right(S(i), i);
            regS((i - 1) / 2) <= S(i) + shift_right(C(i), i) WHEN D(i) = '1' ELSE
                                    S(i) - shift_right(C(i), i);
            regD((i - 1) / 2) <= regS((i - 1) / 2)(23);
            regX((i - 1) / 2) <= X(i);
            regZ((i - 1) / 2) <= Z(i) - A(i + 1) WHEN regD((i - 1) / 2) = '1' ELSE
                                    Z(i) + A(i + 1);
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
            C(i + 1) <= C(i) - shift_right(S(i), i) WHEN D(i) = '1' ELSE
                        C(i) + shift_right(S(i), i);
            S(i + 1) <= S(i) + shift_right(C(i), i) WHEN D(i) = '1' ELSE
                        S(i) - shift_right(C(i), i);
            D(i + 1) <= S(i + 1)(23);
            X(i + 1) <= X(i);
            Z(i + 1) <= Z(i) - A(i + 1) WHEN D(i + 1) = '1' ELSE -- Z requires lookahead to fully make use of 18 iterations
                        Z(i) + A(i + 1);
            END GENERATE regless;
    END GENERATE gen;
END pipe_by_2;

ARCHITECTURE pipe_by_1 OF atan IS
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
    TYPE signed_reg_buf IS ARRAY(0 TO 17) OF signed(23 DOWNTO 0);
    SIGNAL regC, regS, regZ : signed_reg_buf;
    TYPE sgns IS ARRAY(0 TO 18) OF std_logic;
    SIGNAL D : sgns;
    SIGNAL X : sgns;
    TYPE sgns_reg_buf IS ARRAY(0 TO 17) OF std_logic;
    SIGNAL regD : sgns_reg_buf;
    SIGNAL regX : sgns_reg_buf;
    SIGNAL bufC : signed(31 DOWNTO 0);
    SIGNAL bufS : signed(31 DOWNTO 0);
    SIGNAL bufC2 : signed(23 DOWNTO 0);
    SIGNAL bufS2 : signed(23 DOWNTO 0);
    SIGNAL bufX : std_logic;
    SIGNAL bufO : signed(15 DOWNTO 0);
BEGIN
    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            -- x"7FFF" * x"6DED" = x"36F61213"
            bufC <= inputC * x"6DED";
            bufS <= inputS * x"6DED";
            C(0) <= bufC2;
            S(0) <= bufS2;
            X(0) <= bufX;
            output <= bufO;
        END IF;
    END PROCESS;
    bufO <= Z(18)(23 DOWNTO 8) + x"8001" WHEN Z(18)(7) = '1' AND X(18) = '1' ELSE
                        Z(18)(23 DOWNTO 8) + x"0001" WHEN Z(18)(7) = '1' AND X(18) = '0' ELSE
                        Z(18)(23 DOWNTO 8) + x"8000" WHEN Z(18)(7) = '0' AND X(18) = '1' ELSE
                        Z(18)(23 DOWNTO 8);
    bufC2 <= x"36F612" WHEN bufC(31 DOWNTO 8) = x"000000" AND bufS(31 DOWNTO 8) = x"000000" ELSE
            (bufC(31 DOWNTO 8) XOR x"FFFFFF") + x"000001" WHEN bufX = '1' ELSE
            bufC(31 DOWNTO 8);
    bufS2 <= (bufS(31 DOWNTO 8) XOR x"FFFFFF") + x"000001" WHEN bufX = '1' ELSE
            bufS(31 DOWNTO 8);
    bufX <= bufC(31);
    D(0) <= S(0)(23);
    Z(0) <= - A(0) WHEN D(0) = '1' ELSE
            A(0);
    gen : FOR i IN 0 TO 17 GENERATE
        regC(i) <= C(i) - shift_right(S(i), i) WHEN D(i) = '1' ELSE
                                C(i) + shift_right(S(i), i);
        regS(i) <= S(i) + shift_right(C(i), i) WHEN D(i) = '1' ELSE
                                S(i) - shift_right(C(i), i);
        regD(i) <= regS(i)(23);
        regX(i) <= X(i);
        regZ(i) <= Z(i) - A(i + 1) WHEN regD(i) = '1' ELSE
                                Z(i) + A(i + 1);
        PROCESS(Clk)
        BEGIN
            IF rising_edge(Clk) THEN
                C(i + 1) <= regC(i);
                S(i + 1) <= regS(i);
                D(i + 1) <= regD(i);
                X(i + 1) <= regX(i);
                Z(i + 1) <= regZ(i);
            END IF;
        END PROCESS;
    END GENERATE gen;
END pipe_by_1;