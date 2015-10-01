

# Modelsim is 32-bit only
VPI_LIB := vpi
#ARCH:=i686
ROOTPATH = $(PATH)
SIM_ROOT = $(PWD)/../../..
LIB_DIR = $(SIM_ROOT)/build/libs/x86_64:/opt/pym32/lib
QUESTA_PATH=/opt/questa/questa_sv_afv_10.2c_5/questasim/linux/
GUI ?= 0
NOWARNING ?= 1

SIM=Questa
GPI_IMPL=vhpi

ifeq ($(GUI),1)
SIM_CMD = vsim -gui
VSIM_ARGS += -onfinish stop
else
SIM_CMD = vsim -c
VSIM_ARGS += -onfinish exit
endif
ifeq ($(GPI_IMPL),vhpi)
VSIM_ARGS += -foreign \"cocotb_init libfli.so\" -trace_foreign 3
else
VSIM_ARGS += -pli libvpi.so
endif



.PHONY: simrun runsim.do
runsim.do :
	echo "vlib work" > $@
	echo "vopt $(TOPLEVEL) -o $(TOPLEVEL)_opt" >> $@ 
	echo "vsim $(VSIM_ARGS) $(TOPLEVEL)_opt" >> $@
	echo "log -r /*" >> $@
ifneq ($(NOWARNING),0)
	echo "set StdArithNoWarnings 1" >> $@
	echo "set StdNumNoWarnings 1" >> $@
	echo "set NumericStdNoWarnings 1" >> $@
endif
ifneq ($(GUI),1)
	echo "run -all" >> $@
	echo "quit" >> $@
endif

simrun: simulation results.xml
	-@rm -f results.xml
	
clean::
	rm runsim.do
	rm results.xml   

results.xml: runsim.do
	sudo NEWPATH=$(ROOTPATH) -- bash -c 'export LM_LICENSE_FILE=$(LM_LICENSE_FILE); export PATH=$(PATH):$(NEWPATH); export LD_LIBRARY_PATH=$(LIB_DIR):$(LD_LIBRARY_PATH); SIM_ROOT=$(SIM_ROOT) MODULE=$(MODULE) TESTCASE=$(TESTCASE) TOPLEVEL=$(TOPLEVEL) PYTHONPATH=$(LIB_DIR):$(SIM_ROOT):$(PWD):$(PYTHONPATH) $(SIM_CMD) -do runsim.do 2>&1 | tee sim.log'


