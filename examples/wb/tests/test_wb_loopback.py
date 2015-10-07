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
import logging
import os

import cocotb
from cocotb.decorators import coroutine
from cocotb.generators import *
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
from cocotb.wishbone_aux import WishboneOp as WBO
from cocotb.wishbone_aux import WishboneRes as WBR
from cocotb.drivers.wishbone import WishboneMaster
from cocotb.monitors.wishbone import WishboneSlave
import cocotb.generators.word as genw
import cocotb.generators.bit as genb


           
        
def input_thread(L):
    raw_input()
    L.append(None)
    

class rec():
    cntcyc = 0
    firsttime = True
    dut = None
    
    def __init__(self, dut):
        self.cntcyc = 0
        self.dut = dut
        
    def receive(self, result):
        if self.firsttime:
            self.firsttime = False
            self.dut.log.info("****** Slave - Received Operations:")
            
        self.dut.log.info("WBS Cycle #%3u, %3u Ops" % (self.cntcyc,len(result)))
        self.cntcyc += 1
        cnt = 0
        for op in result:
            dat = "      None"
            if op.dat is not None:
                dat = "0x%08x" % op.dat            
            self.dut.log.debug("#%3u ADR: 0x%08x DAT: %s IDLW: %3u SEL: 0x%x" % (cnt, op.adr, dat, op.idle, op.sel))
            cnt += 1


        

@cocotb.test()
def test_wb_looback(dut):
    clkref_period = 8
    clksys_period = 16
    
#    """Example of a test using TUN/TAP over WB."""
    cocotb.fork(Clock(dut.clk, clkref_period).start())
    cocotb.fork(Clock(dut.clk2, clksys_period).start())
    
    
    
    
    # Reset the DUT
    dut.log.debug("Resetting DUT")
    dut.reset_n <= 0
    dut.reset_n2 <= 0
    
   
    yield Timer(50*clksys_period)
 
    dut.log.debug("Out of reset")
    dut.log.setLevel(logging.INFO)
    

    tsGen           = genw.random_data(0, 1000, 64)
    idleGenWord     = genw.random_data(0, 5)
    replyWaitGen     = genw.random_data(1, 10)
    idleGenBlock    = genw.random_data(0, 50)
    stallGen        = genb.bit_toggler(genw.random_data(1, 10), genw.random_data(1, 10))
    cntGenX1000     = genw.incrementing_data(0x1000)
    cntGen          = genw.incrementing_data(1)
    stdExp          = WBR(True, None, 6, 5, 5)    
    datGen          = genw.incrementing_data(1)
    errGen          = genb.bit_toggler(genw.random_data(0, 1), genw.random_data(1, 10))
    adrGen          = genw.random_data(0, 50)
    datwrGen        = genw.random_data()
    wordRepeatGen   = genw.random_data(1, 50)
    weGen           = genw.random_data(0, 1)
    
    output = rec(dut)
    
    wbm  = WishboneMaster(dut, "wbm", dut.clk)
    wbm.log.setLevel(logging.INFO)
    
    wbs  = WishboneSlave(entity=dut, name="wbmo", clock=dut.clk, callback=output.receive, errgen=None, datgen=datGen, stallwaitgen=stallGen, replywaitgen=replyWaitGen)
    wbs.log.setLevel(logging.INFO)    
    
    oplist = []
    explist = []
    reslist = []  
    
    #oplist.append([WBO(0x0, 0xDEADBEEF, 123)])    
    
#    for i in range(1, 3):
#        tmpOplist = []
#        tmpExplist = []
#        ts = tsGen.next()
#
#        tmpOplist.append(WBO(0x0, ts >> 32,          idleGenWord.next()))
#        tmpExplist.append(stdExp)
#        tmpOplist.append(WBO(0x0, ts & 0xffffffff,   idleGenWord.next()))
#        tmpOplist.append(WBO(0x0, None,   idleGenWord.next()))
#        tmpExplist.append(stdExp)
#        n = cntGenX1000.next()
#        tmpOplist.append(WBO(0x0, n + cntGen.next(), idleGenWord.next()))
#        tmpExplist.append(stdExp)
#        tmpOplist.append(WBO(0x0, n + cntGen.next(), idleGenWord.next()))
#        tmpExplist.append(stdExp)
#        tmpOplist.append(WBO(0x0, n + cntGen.next(), idleGenWord.next()))
#        tmpExplist.append(stdExp)
#        tmpOplist.append(WBO(0x0, n + cntGen.next(), idleGenWord.next()))
#        tmpExplist.append(stdExp)
#        tmpOplist.append(WBO(0x0, n + cntGen.next(), idleGenWord.next()))
#        tmpExplist.append(stdExp)
#        tmpOplist.append(WBO(0x0, None, idleGenBlock.next()))
#        
#        tmpExplist.append(stdExp)
#        oplist += [tmpOplist]
#        explist.append(tmpExplist)
   
    
    for i in range(0, 10):
        tmpOplist = []
        words = wordRepeatGen.next()        
        for i in range(0, words):        
            dat = None        
            if weGen.next():
                dat = datwrGen.next()
            tmpOplist.append(WBO(adrGen.next()*4, dat, idleGenWord.next()))
        oplist += [tmpOplist]    
    
    for cycle in oplist:
        tmp = yield wbm.send_cycle(cycle)
        reslist.append(tmp)     
    
    
    dut.log.info("***** Master - Received Replies:")
    cyccnt = 0    
    
    for cycle in reslist:
        dut.log.info("WBM Cycle #%3u, %3u Ops" % (cyccnt,len(cycle)))
        cyccnt += 1
        cnt = 0
        for res in cycle:
            dat = "      None"
            if res.dat is not None:
                dat = "0x%08x" % res.dat

            ackerr = "ERR"                
            if res.ack:
                ackerr = "ACK"
                
            dut.log.debug("#%3u ACK/ERR: %s RD: %s IDLW: %3u STLW: %3u ACKW: %3u" % (cnt, ackerr, dat, res.waitidle, res.waitstall, res.waitack))
            cnt += 1
#    yield RisingEdge(dut.clk)
  
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
       
   
    
    
        
