''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

''' extremely modified ping example - Mathias Kreider March 2015 '''

import time
import random
import logging
import sys
import fcntl
import os
import struct
import subprocess
import thread

import cocotb
from cocotb.decorators import coroutine
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
from cocotb.drivers.wishbone import WishboneOp as WBO
from cocotb.drivers.wishbone import WishboneMaster


@cocotb.coroutine
def lifesign(dut, wait):
    yield RisingEdge(dut.clk2)
    count = 0;
    while True:
       yield Timer(wait)
       count += 1
       myStr = "Running - %u us" % (wait*count/1000)
       dut.log.info(myStr)

@cocotb.coroutine
def uart_printer(dut):
    yield RisingEdge(dut.reset_n2)
    while True:
        yield RisingEdge(dut.clk2)
        if int(dut.uart_out_valid) == 1:
           sys.stderr.write(str(unichr(dut.uart_out)))
           
        
def input_thread(L):
    raw_input()
    L.append(None)
    
  
def def_clks():
    global clkref_period
    global clksys_period
    clkref_period = 80
    clksys_period = 160


@cocotb.coroutine
def writelist(avm, ops):
    for n in ops:
        yield avm.write(ops(0), ops(1))


@cocotb.test()
def test_wb(dut):
    def_clks()
    
#    """Example of a test using TUN/TAP over WB."""
    cocotb.fork(Clock(dut.clk, clkref_period).start())
    cocotb.fork(Clock(dut.clk2, clksys_period).start())
    
    
    
    
    # Reset the DUT
    dut.log.debug("Resetting DUT")
    dut.reset_n <= 0
    dut.reset_n2 <= 0
    
   
    yield Timer(50*clksys_period)
    yield RisingEdge(dut.clk)
    dut.reset_n <= 1
    yield RisingEdge(dut.clk2)
    dut.reset_n2 <= 1
    dut.log.debug("Out of reset")
    
    wbm  = WishboneMaster(dut, "wbm", dut.clk, 10, 5)
    wbm.log.setLevel(logging.DEBUG) 
    oplist = []
    oplist.append(WBO(0x0))
    oplist.append(WBO(0x0, True, 123))
    oplist.append(WBO(0x0))
    oplist.append(WBO(0x0))
    oplist.append(WBO(0x0, True, 456))
    oplist.append(WBO(0x0))
    oplist.append(WBO(0x0, True, 789))
    oplist.append(WBO(0x0))
    
    
    
    yield RisingEdge(dut.clk)
    test = []
    test0 = yield wbm.send_cycle(oplist)
    test1 = yield wbm.send_cycle(oplist, False)
    test2 = yield wbm.send_cycle(oplist)
    test = test0 + test1 + test2    
    print test
    yield RisingEdge(dut.clk)
  
    #cocotb.fork(lifesign(dut, 5000000))    

  #  L = []
   # thread.start_new_thread(input_thread, (L,))
  #  print "Press Any key to close"
  #  while True:
  #     if L: 
  #        print L
  #        break
  #     yield RisingEdge(dut.clk2)

    print "DONE *****"
       
   
    
    
        
