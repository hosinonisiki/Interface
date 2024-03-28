LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

PACKAGE MyPak_PID IS
  FUNCTION word_length(gain : INTEGER) RETURN INTEGER;
END MyPak_PID;

PACKAGE BODY MyPak_PID IS
  FUNCTION word_length(gain : INTEGER) RETURN INTEGER IS
  BEGIN
    IF gain >= 0 THEN
      RETURN 32;
    ELSE
      RETURN 32 - gain;
    END IF;
  END word_length;
END MyPak_PID;

LIBRARY IEEE;
USE IEEE.std_logic_1164.ALL;
USE IEEE.Numeric_std.ALL;

LIBRARY Moku;
USE Moku.Support.ALL;

USE work.MyPak_PID.ALL;

ENTITY PID IS
  GENERIC(
    gain_P : INTEGER := 8;
    gain_I : INTEGER := -16;
    gain_D : INTEGER := 0
    -- count in bits, positive is gain and negative is attenuation
    -- attenuation is done by taking the MSB of a channel with more than 32 bits
    -- gain is done by taking the LSB of input and pad k coefficients with 0s
    -- cuz using gain means the input signal is sufficiently small to take the LSB without losing precision
    -- it should be left to the user that the channels won't overflow

    -- corner sets at omega where omega * delta_t = 1
    -- given that delta_t = 3.2ns, omega = 1 / 3.2ns = 312.5MHz, f = omega / 2pi = 49.7MHz
    -- 24 bit gain = 16777216, giving corner at 2.965Hz, 8 bit gain = 256, giving corner at 194kHz
  );
  PORT(
    -- ports are formalized to 16 bits
    actual : IN signed(15 DOWNTO 0);
    setpoint : IN signed(15 DOWNTO 0);
    control : OUT signed(15 DOWNTO 0);
    Test : OUT signed(15 DOWNTO 0);

    K_P : IN signed(15 DOWNTO 0); 
    K_I : IN signed(15 DOWNTO 0); 
    K_D : IN signed(15 DOWNTO 0); 

    limit_P : IN signed(15 DOWNTO 0);
    limit_I : IN signed(15 DOWNTO 0);
    limit_D : IN signed(15 DOWNTO 0);

    limit_sum : IN signed(15 DOWNTO 0);

    Reset : IN std_logic;
    Clk : IN std_logic
  );
END PID;

ARCHITECTURE bhvr OF PID IS
  SIGNAL error : signed(15 DOWNTO 0);
  SIGNAL last_error : signed(15 DOWNTO 0) := x"0000";
  SIGNAL difference : signed(15 DOWNTO 0);
  SIGNAL sum : signed(15 DOWNTO 0);

  SIGNAL buf_sum : signed(17 DOWNTO 0);

  SIGNAL P : signed(word_length(gain_P) - 1 DOWNTO 0) := (OTHERS => '0');
  SIGNAL I : signed(word_length(gain_I) - 1 DOWNTO 0) := (OTHERS => '0');
  SIGNAL D : signed(word_length(gain_D) - 1 DOWNTO 0) := (OTHERS => '0');

  SIGNAL buf_P : signed(word_length(gain_P) - 1 DOWNTO 0);
  SIGNAL buf_I : signed(word_length(gain_I) - 1 DOWNTO 0);
  SIGNAL buf_D : signed(word_length(gain_D) - 1 DOWNTO 0);

  SIGNAL reg_P : signed(word_length(gain_P) - 1 DOWNTO 0);
  SIGNAL reg_I : signed(word_length(gain_I) - 1 DOWNTO 0);
  SIGNAL reg_D : signed(word_length(gain_D) - 1 DOWNTO 0);

  SIGNAL reg_buf_P : signed(word_length(gain_P) - 1 DOWNTO 0);
  SIGNAL reg_buf_I : signed(word_length(gain_I) - 1 DOWNTO 0);
  SIGNAL reg_buf_D : signed(word_length(gain_D) - 1 DOWNTO 0);
BEGIN

  PROCESS(Reset)
  BEGIN
  END PROCESS;

  PID : PROCESS(Clk)
  BEGIN
    IF rising_edge(Clk) THEN
        IF Reset = '1' THEN
            P <= (OTHERS => '0');
            I <= (OTHERS => '0');
            D <= (OTHERS => '0');
            buf_P <= (OTHERS => '0');
            buf_I <= (OTHERS => '0');
            buf_D <= (OTHERS => '0');
        ELSE
            P <= reg_P;
            I <= reg_I;
            D <= reg_D;
            buf_P <= reg_buf_P;
            buf_I <= reg_buf_I;
            buf_D <= reg_buf_D;
        END IF;
        last_error <= error;
        error <= actual - setpoint;
        difference <= error - last_error;
        control <= sum;
    END IF;
  END PROCESS PID;
  reg_buf_P <= K_P * (error(15) & error(14 - gain_P DOWNTO 0) & (gain_P - 1 DOWNTO 0 => '0')) WHEN gain_P > 0 ELSE
                ((-gain_P - 1 DOWNTO 0 => K_P(15)) & K_P) * error WHEN gain_P < 0 ELSE
                K_P * error; -- there could be a better way to implement 8-bit gain?
  reg_buf_I <= I + K_I * (error(15) & error(14 - gain_I DOWNTO 0) & (gain_I - 1 DOWNTO 0 => '0')) WHEN gain_I > 0 ELSE
                I + ((-gain_I - 1 DOWNTO 0 => K_I(15)) & K_I) * error WHEN gain_I < 0 ELSE
                I + K_I * error;
  reg_buf_D <= K_D * (difference(15) & difference(14 - gain_D DOWNTO 0) & (gain_D - 1 DOWNTO 0 => '0')) WHEN gain_D > 0 ELSE
                ((-gain_D - 1 DOWNTO 0 => K_D(15)) & K_D) * difference WHEN gain_D < 0 ELSE
                K_D * difference;

  reg_P <= limit_P & (word_length(gain_P) - 17 DOWNTO 0 => '0') WHEN buf_P > limit_P & (word_length(gain_P) - 17 DOWNTO 0 => '0') ELSE
          -limit_P & (word_length(gain_P) - 17 DOWNTO 0 => '0') WHEN buf_P < -limit_P & (word_length(gain_P) - 17 DOWNTO 0 => '0') ELSE
          buf_P;
  reg_I <= limit_I & (word_length(gain_I) - 17 DOWNTO 0 => '0') WHEN buf_I > limit_I & (word_length(gain_I) - 17 DOWNTO 0 => '0') ELSE
          -limit_I & (word_length(gain_I) - 17 DOWNTO 0 => '0') WHEN buf_I < -limit_I & (word_length(gain_I) - 17 DOWNTO 0 => '0') ELSE
          buf_I;
  reg_D <= limit_D & (word_length(gain_D) - 17 DOWNTO 0 => '0') WHEN buf_D > limit_D & (word_length(gain_D) - 17 DOWNTO 0 => '0') ELSE
          -limit_D & (word_length(gain_D) - 17 DOWNTO 0 => '0') WHEN buf_D < -limit_D & (word_length(gain_D) - 17 DOWNTO 0 => '0') ELSE
          buf_D;

  buf_sum <= ((1 DOWNTO 0 => P(word_length(gain_P) - 1)) & P(word_length(gain_P) - 1 DOWNTO word_length(gain_P) - 16)) + ((1 DOWNTO 0 => I(word_length(gain_I) - 1)) & I(word_length(gain_I) - 1 DOWNTO word_length(gain_I) - 16)) + ((1 DOWNTO 0 => D(word_length(gain_D) - 1)) & D(word_length(gain_D) - 1 DOWNTO word_length(gain_D) - 16)); -- this should not overflow in a normal operation

  sum <= limit_sum WHEN buf_sum > ("00" & limit_sum) ELSE
          -limit_sum WHEN buf_sum < -("00" & limit_sum) ELSE
          buf_sum(15 DOWNTO 0);

  Test <= I(word_length(gain_I) - 1 DOWNTO word_length(gain_I) - 16);

END bhvr;