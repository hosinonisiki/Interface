LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

-- potential problem : a 1 clock delay in I channel
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
        -- may needs lookahead
        
        limit_I : IN signed(63 DOWNTO 0);

        limit_sum : IN signed(15 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END PID;

ARCHITECTURE bhvr OF PID IS
    SIGNAL error : signed(15 DOWNTO 0);
    SIGNAL last_error : signed(15 DOWNTO 0) := x"0000";
    SIGNAL buf_sum : signed(47 DOWNTO 0);
    SIGNAL sum : signed(15 DOWNTO 0);

    SIGNAL buf_K_P : signed(31 DOWNTO 0);
    SIGNAL buf_K_I : signed(31 DOWNTO 0);
    SIGNAL buf_K_D : signed(31 DOWNTO 0);

    SIGNAL P : signed(47 DOWNTO 0);
    SIGNAL I : signed(63 DOWNTO 0);
    SIGNAL D : signed(47 DOWNTO 0);

    SIGNAL reg_P : signed(47 DOWNTO 0);
    SIGNAL reg_I : signed(63 DOWNTO 0);
    SIGNAL reg_D : signed(47 DOWNTO 0);

    SIGNAL buf_I : signed(47 DOWNTO 0);
    SIGNAL reg_buf_I : signed(47 DOWNTO 0);
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
            control <= sum;
            buf_K_P <= K_P;
            buf_K_I <= K_I;
            buf_K_D <= K_D;
            buf_I <= reg_buf_I;
        END IF;
    END PROCESS PID;    

    reg_P <= buf_K_P * error;
    
    reg_buf_I <= buf_K_I * error;
    reg_I <= limit_I WHEN I + ((15 DOWNTO 0 => buf_I(47)) & buf_I) > limit_I ELSE
                -limit_I WHEN I + ((15 DOWNTO 0 => buf_I(47)) & buf_I) < -limit_I ELSE
                I + ((15 DOWNTO 0 => buf_I(47)) & buf_I);

    reg_D <= buf_K_D * (error - last_error);

    buf_sum <= P + I(63 DOWNTO 16) + (x"00000000000" & "000" & I(15)) + D;

    sum <= limit_sum WHEN buf_sum(47 DOWNTO 16) > (x"0000" & limit_sum) ELSE
               -limit_sum WHEN buf_sum(47 DOWNTO 16) - x"00000001" < -(x"0000" & limit_sum) ELSE
               buf_sum(31 DOWNTO 16);
END bhvr;