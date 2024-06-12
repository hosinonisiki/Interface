LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

ENTITY PID_wrapped IS
    PORT(
        actual : IN signed(15 DOWNTO 0);
        setpoint : IN signed(15 DOWNTO 0);
        control : OUT signed(15 DOWNTO 0);

        K_P : IN signed(31 DOWNTO 0);
        K_I : IN signed(31 DOWNTO 0);
        K_D : IN signed(31 DOWNTO 0);
        
        threshold_I : IN signed(63 DOWNTO 0);
        wrapped_I : IN signed(63 DOWNTO 0);

        holding_time : IN unsigned(31 DOWNTO 0);

        limit_sum : IN signed(15 DOWNTO 0);

        Reset : IN std_logic;
        Clk : IN std_logic
    );
END PID_wrapped;

ARCHITECTURE nodecay OF PID_wrapped IS
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

    SIGNAL counter : unsigned(31 DOWNTO 0) := (OTHERS => '0');
    type state_type is (s_freerun, s_holding);
    SIGNAL state : state_type := s_freerun;
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
    FSM : PROCESS(Clk)
    BEGIN
        IF rising_edge(Clk) THEN
            IF Reset = '1' THEN
                state <= s_freerun;
                counter <= (OTHERS => '0');
                reg_I <= (OTHERS => '0');
            ELSE
                IF state = s_freerun THEN
                    IF I > threshold_I THEN
                        state <= s_holding;
                        counter <= holding_time;
                        reg_I <= -wrapped_I;
                    ELSIF I < -threshold_I THEN
                        state <= s_holding;
                        counter <= holding_time;
                        reg_I <= wrapped_I;
                    ELSE
                        reg_I <= I + ((15 DOWNTO 0 => buf_I(47)) & buf_I);
                    END IF;
                ELSE
                    IF counter = 0 THEN
                        state <= s_freerun;
                    ELSE
                        counter <= counter - 1;
                    END IF;
                END IF;
            END IF;
        END IF;
    END PROCESS FSM;
    
    reg_D <= buf_K_D * difference;

    buf_sum <= P + I(63 DOWNTO 16) + (x"00000000000" & "000" & I(15)) + D;

    sum <= limit_sum WHEN buf_sum(47 DOWNTO 16) > (x"0000" & limit_sum) ELSE
               -limit_sum WHEN buf_sum(47 DOWNTO 16) - x"00000001" < -(x"0000" & limit_sum) ELSE
               buf_sum(31 DOWNTO 16);
END nodecay;