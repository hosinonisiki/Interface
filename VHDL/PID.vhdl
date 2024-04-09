LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY PID IS
    PORT(
        actual : IN signed(15 DOWNTO 0);
        setpoint : IN signed(15 DOWNTO 0);
        control : OUT signed(15 DOWNTO 0);

        K_P : IN signed(31 DOWNTO 0);
        K_I : IN signed(31 DOWNTO 0);
        K_D : IN signed(31 DOWNTO 0);

        -- There is no need to set a limit on P/D channel
        -- since no accumulation is made and it should be left to the user
        -- to ensure that no overflow occurs.

        -- future feature: I channel with decay
        -- I[n] = qI[n-1] + x[n] = qqI[n-2] + qx[n-1] + x[n], 2-lookahead
        
        limit_I : IN signed(47 DOWNTO 0);

        limit_sum : IN signed(15 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END PID;

ARCHITECTURE bhvr OF PID IS
    SIGNAL error : signed(15 DOWNTO 0);
    SIGNAL last_error : signed(15 DOWNTO 0) := x"0000";
    SIGNAL sum : signed(47 DOWNTO 0);

    SIGNAL P : signed(47 DOWNTO 0);
    SIGNAL I : signed(47 DOWNTO 0);
    SIGNAL D : signed(47 DOWNTO 0);

    SIGNAL reg_P : signed(47 DOWNTO 0);
    SIGNAL reg_I : signed(47 DOWNTO 0);
    SIGNAL reg_D : signed(47 DOWNTO 0);

    SIGNAL buf_P : signed(47 DOWNTO 0);
    SIGNAL buf_I : signed(47 DOWNTO 0);
    SIGNAL buf_D : signed(47 DOWNTO 0);
BEGIN
    PID : PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                P <= (OTHERS => '0');
                I <= (OTHERS => '0');
                D <= (OTHERS => '0');
            ELSE
                P <= reg_P;
                I <= reg_I;
                D <= reg_D;
            END IF;
            last_error <= error;
            error <= actual - setpoint;
        END IF;
    END PROCESS PID;    

    reg_P <= K_P * error;
    
    buf_I <= I + K_I * error;
    reg_I <= limit_I WHEN buf_I > limit_I ELSE
                -limit_I WHEN buf_I < -limit_I ELSE
                buf_I;

    reg_D <= K_D * (error - last_error);

    sum <= P + I + D;

    control <= limit_sum WHEN sum(47 DOWNTO 16) > (x"0000" & limit_sum) ELSE
               -limit_sum WHEN sum(47 DOWNTO 16) - x"00000001" < -(x"0000" & limit_sum) ELSE
               sum(31 DOWNTO 16);
END bhvr;