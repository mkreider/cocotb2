library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.wishbone_pkg.all;
use work.genram_pkg.all;
use work.prio_pkg.all;

entity cocotb_prio2 is
  port (
    clk           : in  std_logic;
    reset_n       : in  std_logic;
    
    clk2          : in  std_logic;
    reset_n2      : in  std_logic;
    
    wbs_cyc       : in  std_logic;
    wbs_stb       : in  std_logic;
    wbs_we        : in  std_logic;
    wbs_sel       : in  std_logic_vector(3 downto 0);  
    wbs_adr       : in  std_logic_vector(31 downto 0);
    wbs_datrd     : out std_logic_vector(31 downto 0);  
    wbs_datwr     : in  std_logic_vector(31 downto 0);
          
    --wbs_stall     : out std_logic;
    wbs_ack       : out std_logic;
    wbs_err       : out std_logic;

    wbm_cyc      : out std_logic;
    wbm_stb      : out std_logic;
    wbm_we       : out std_logic;
    wbm_sel      : out std_logic_vector(3 downto 0);
    wbm_adr      : out std_logic_vector(31 downto 0);
    wbm_datrd    : in  std_logic_vector(31 downto 0);
    wbm_datwr    : out std_logic_vector(31 downto 0);

    wbm_err      : in  std_logic;
    wbm_stall    : in  std_logic;
    wbm_ack      : in  std_logic;
    
    ts_out        : out std_logic_vector(63 downto 0);
    ts_valid_out  : out std_logic;
    en_in         : in  std_logic

  
    );
end entity;

architecture rtl of cocotb_prio2 is

  signal s_master_out : t_wishbone_master_out;
  signal s_slave_out  : t_wishbone_slave_out;   
  signal s_master_in : t_wishbone_master_in;
  signal s_slave_in  : t_wishbone_slave_in;

   
   
   
begin

   -- in from TB Slave to DUT Master
  wbm_we    <= s_master_out.we;
  wbm_stb   <= s_master_out.stb;
  wbm_datwr <= s_master_out.dat;
  wbm_adr   <= s_master_out.adr;
  wbm_sel   <= s_master_out.sel;
  wbm_cyc   <= s_master_out.cyc;

 
  -- out from DUT Master to TB Slave
  s_master_in.dat   <= wbm_datrd;
  s_master_in.ack   <= wbm_ack;
  s_master_in.stall <= wbm_stall;
  s_master_in.err   <= wbm_err;

  -- in from TB Master to DUT Slave
  s_slave_in.we <= wbs_we;
  s_slave_in.stb <= wbs_stb;
  s_slave_in.dat <= wbs_datwr;
  s_slave_in.adr <= wbs_adr;
  s_slave_in.sel <= wbs_sel ;
  s_slave_in.cyc <= wbs_cyc;

-- out from TB Master to DUT Slave
  wbs_datrd <= s_slave_out.dat;
  wbs_ack  <= s_slave_out.ack;
  wbs_err  <= s_slave_out.err;
  --wbs_stall  <= s_slave_out.stall;  



  
  dut : queue_unit 
  generic map(
    g_depth => 32,
    g_words => 8
  )
  port map(
    clk_i       => clk,
    rst_n_i     => reset_n,

    master_o    => s_master_out,
    master_i    => s_master_in,

    slave_i     => s_slave_in,
    slave_o     => s_slave_out,

    ts_o        => ts_out,
    ts_valid_o  => ts_valid_out,

    sel_i       => en_in

  );

   

end architecture;
