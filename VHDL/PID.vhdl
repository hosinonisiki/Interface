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
        
        limit_I : IN signed(63 DOWNTO 0);

        limit_sum : IN signed(15 DOWNTO 0);

        decay_I : IN signed(31 DOWNTO 0); -- let x40000000 represent 1.0

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END PID;

ARCHITECTURE bhvr OF PID IS
    SIGNAL error : signed(15 DOWNTO 0);
    SIGNAL last_error : signed(15 DOWNTO 0) := x"0000";
    SIGNAL difference : signed(15 DOWNTO 0);
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

    -- I[n] = x[n] * coef1 + x[n-1] * coef2 + I[n-2] * coef3
    SIGNAL coef1 : signed(31 DOWNTO 0);
    SIGNAL coef2 : signed(31 DOWNTO 0);
    SIGNAL coef3 : signed(31 DOWNTO 0);

    SIGNAL reg_coef1 : signed(31 DOWNTO 0);
    SIGNAL reg_coef2 : signed(63 DOWNTO 0);
    SIGNAL reg_coef3 : signed(63 DOWNTO 0);

    SIGNAL product1: signed(47 DOWNTO 0);
    SIGNAL product2: signed(47 DOWNTO 0);

    SIGNAL reg_product1: signed(47 DOWNTO 0);
    SIGNAL reg_product2: signed(47 DOWNTO 0);

    SIGNAL sum1 : signed(47 DOWNTO 0);
    SIGNAL sum2 : signed(47 DOWNTO 0);

    SIGNAL reg_sum1 : signed(47 DOWNTO 0);
    SIGNAL reg_sum2 : signed(47 DOWNTO 0);

    SIGNAL decayed : signed(63 DOWNTO 0);

    SIGNAL reg_decayed : signed(95 DOWNTO 0);
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
            difference <= error - last_error;
            control <= sum;
            buf_K_P <= K_P;
            buf_K_I <= K_I;
            buf_K_D <= K_D;
            coef1 <= reg_coef1;
            coef2 <= reg_coef2(61 DOWNTO 30);
            coef3 <= reg_coef3(61 DOWNTO 30);

            product1 <= reg_product1;
            product2 <= reg_product2;

            sum1 <= reg_sum1;
            sum2 <= reg_sum2;

            decayed <= reg_decayed(93 DOWNTO 30);
        END IF;
    END PROCESS PID;    

    reg_P <= buf_K_P * error;

    reg_I <= limit_I WHEN decayed > limit_I ELSE
                -limit_I WHEN decayed < -limit_I ELSE
                decayed + ((15 DOWNTO 0 => sum1(47)) & sum1);
    
    reg_D <= buf_K_D * difference;

    buf_sum <= P + I(63 DOWNTO 16) + (x"00000000000" & "000" & I(15)) + D;

    sum <= limit_sum WHEN buf_sum(47 DOWNTO 16) > (x"0000" & limit_sum) ELSE
               -limit_sum WHEN buf_sum(47 DOWNTO 16) - x"00000001" < -(x"0000" & limit_sum) ELSE
               buf_sum(31 DOWNTO 16);

    reg_coef1 <= buf_K_I;
    reg_coef2 <= buf_K_I * decay_I;
    reg_coef3 <= decay_I * decay_I;

    reg_product1 <= coef1 * error;
    reg_product2 <= coef2 * error;

    reg_sum1 <= sum2 + product1;
    reg_sum2 <= product2;

    reg_decayed <= coef3 * I;
END bhvr;

ARCHITECTURE nodecay OF PID IS
    SIGNAL error : signed(15 DOWNTO 0);
    SIGNAL last_error : signed(15 DOWNTO 0) := x"0000";
    SIGNAL difference : signed(15 DOWNTO 0);
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
            difference <= error - last_error;
            control <= sum;
            buf_K_P <= K_P;
            buf_K_I <= K_I;
            buf_K_D <= K_D;
            buf_I <= reg_buf_I;
        END IF;
    END PROCESS PID;    

    reg_P <= buf_K_P * error;
    
    reg_buf_I <= buf_K_I * error;
    reg_I <= limit_I WHEN I > limit_I ELSE
                -limit_I WHEN I < -limit_I ELSE
                I + ((15 DOWNTO 0 => buf_I(47)) & buf_I);

    
    reg_D <= buf_K_D * difference;

    buf_sum <= P + I(63 DOWNTO 16) + (x"00000000000" & "000" & I(15)) + D;

    sum <= limit_sum WHEN buf_sum(47 DOWNTO 16) > (x"0000" & limit_sum) ELSE
               -limit_sum WHEN buf_sum(47 DOWNTO 16) - x"00000001" < -(x"0000" & limit_sum) ELSE
               buf_sum(31 DOWNTO 16);
END nodecay;

-- architecture migrated from the module running on AXKU041
-- notice the difference in width of various signals
ARCHITECTURE optimized OF PID IS
    SIGNAL error : signed(15 DOWNTO 0);
    SIGNAL error_1 : signed(15 DOWNTO 0);
    SIGNAL differential : signed(15 DOWNTO 0);
    SIGNAL integral : signed(47 DOWNTO 0);

    SIGNAL gain_p : signed(23 DOWNTO 0);
    SIGNAL gain_i : signed(31 DOWNTO 0);
    SIGNAL gain_d : signed(23 DOWNTO 0);

    SIGNAL product_p : signed(39 DOWNTO 0);
    SIGNAL product_i : signed(47 DOWNTO 0);
    SIGNAL product_d : signed(39 DOWNTO 0);

    SIGNAL limit_integral : signed(47 DOWNTO 0);
    SIGNAL limit_sum_padded : signed(27 DOWNTO 0);

    SIGNAL integral_buf : signed(47 DOWNTO 0);
    SIGNAL integral_buf_limited : signed(47 DOWNTO 0);
    SIGNAL sum_buf : signed(27 DOWNTO 0);
    SIGNAL sum_buf_limited : signed(27 DOWNTO 0);
BEGIN
    gain_p <= K_P(23 DOWNTO 0);
    gain_i <= K_I;
    gain_d <= K_D(23 DOWNTO 0);
    limit_integral <= limit_I(55 DOWNTO 8);
    limit_sum_padded <= x"00" & limit_sum & x"0";

    PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                integral <= (OTHERS => '0');
            ELSE
                error <= actual - setpoint;
                error_1 <= error;
                differential <= error - error_1;
                integral <= integral_buf_limited;
                product_p <= gain_p * error;
                product_i <= gain_i * error;
                product_d <= gain_d * differential;
                control <= sum_buf_limited(19 DOWNTO 4);
            END IF;
        END IF;
    END PROCESS;

    integral_buf <= integral + ((7 DOWNTO 0 => product_i(47)) & product_i(47 DOWNTO 8)) + ((46 DOWNTO 0 => '0') & product_i(7));
    integral_buf_limited <= limit_integral WHEN integral_buf > limit_integral ELSE
                            -limit_integral WHEN integral_buf < -limit_integral ELSE
                            integral_buf;

    sum_buf <= product_p(39 DOWNTO 12) + integral_buf_limited(47 DOWNTO 20) + product_d(39 DOWNTO 12);
    sum_buf_limited <= limit_sum_padded WHEN sum_buf > limit_sum_padded ELSE
                    -limit_sum_padded WHEN sum_buf < -limit_sum_padded ELSE
                    sum_buf;
END optimized;