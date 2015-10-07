###################################
## enter your project details here
testmodule  = "test_wb_loopback"
testcase    = ""
top_module  = "cocotb_wb_loopback"
##################################

target         = "altera"
action         = "simulation"
syn_device     = ""
sim_tool       = "modelsim"
vcom_opt       = "-O5 -vopt"
vlog_opt       = "-O5 -vopt -timescale 1ns/100ps -mfcu +acc=rmb -sv"

sim_pre_cmd    = "$(eval LM_LICENSE_FILE = 1717@lxcad01)\n\t$(eval TOPLEVEL = %s)\n\t$(eval MODULE = %s)\n\t$(eval TESTCASE = %s)\n\t@echo Hallo $(TOPLEVEL)" % (top_module, testmodule, testcase)
incl_makefiles = ["build.mk"]

modules = {
  "local" : [ 
    "../hdl",
    "../../../../beldebug/modules/prioq2",
    "../../../../beldebug/ip_cores/general-cores/modules/wishbone",
    "../../../../beldebug/ip_cores/general-cores/modules/genrams",
    "../../../../beldebug/ip_cores/general-cores/modules/common", 
  ]
}


