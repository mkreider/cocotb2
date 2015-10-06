library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.wishbone_pkg.all;
use work.genram_pkg.all;

entity cocotb_bus is
	port (
		clk: in std_logic;
		reset_n : in std_logic;
		
		clk2  : in std_logic;
		reset_n2 : in std_logic;
		
		wbm_cyc : in std_logic;
		wbm_stb : in std_logic;
		wbm_we : in std_logic;
		wbm_sel : in std_logic_vector(3 downto 0);	
		wbm_adr : in std_logic_vector(31 downto 0);
		wbm_datrd : out std_logic_vector(31 downto 0);	
		wbm_datwr : in std_logic_vector(31 downto 0);
	        
		wbm_stall: out std_logic;
		wbm_ack: out std_logic;
		wbm_err: out std_logic;

		wbmo_cyc : out std_logic;
                wbmo_stb : out std_logic;
                wbmo_we : out std_logic;
                wbmo_sel : out std_logic_vector(3 downto 0);
                wbmo_adr : out std_logic_vector(31 downto 0);
                wbmo_datrd : in std_logic_vector(31 downto 0);
                wbmo_datwr : out std_logic_vector(31 downto 0);

                wbmo_stall: in std_logic;
                wbmo_ack: in std_logic;
                wbmo_err: in std_logic

  
		);
end entity;

architecture rtl of cocotb_bus is

   
  signal s_master_in : t_wishbone_master_in;
   signal s_master_out  : t_wishbone_master_out;
signal reg : std_logic_vector(31 downto 0);   
   
   
   
begin

	s_master_out.we <= wbm_we;
	s_master_out.stb <= wbm_stb;
	s_master_out.dat <= wbm_datwr;
	s_master_out.adr <= wbm_adr;
	s_master_out.sel <= x"f";
	s_master_out.cyc <= wbm_cyc;

--	s_master_in.dat <= reg;
	wbm_datrd <= s_master_in.dat;
	wbm_ack <= s_master_in.ack;
	wbm_stall <= s_master_in.stall;

	wbmo_we  <= s_master_out.we;
        wbmo_stb <= s_master_out.stb;
        wbmo_datwr <= s_master_out.dat;
        wbmo_adr <= s_master_out.adr;
        wbmo_sel <= s_master_out.sel;
        wbmo_cyc <= s_master_out.cyc;

        s_master_in.dat <= wbmo_datrd;
        s_master_in.ack <= wbmo_ack;
        s_master_in.stall <= wbmo_stall;	

--	main : process(clk)
--	begin
--		if(rising_edge(clk)) then
--			if(reset_n = '0') then
--				s_master_in.stall <= '0';
--				s_master_in.ack <= '0';
--				s_master_in.err <= '0';
--				reg <= (others => '0');	
--			else
--				s_master_in.ack <= '0';
--				if((s_master_out.cyc and s_master_out.stb and not s_master_in.stall) = '1') then
--					if(s_master_out.we = '1') then
--						reg <= s_master_out.dat;
--					end if;
--					s_master_in.ack <= '1';	
--				end if;
--			end if;
--		end if;
--	end process;

   

end architecture;
