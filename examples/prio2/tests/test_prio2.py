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
import random
import Queue

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
from cocotb.result import TestFailure, TestSuccess, ReturnValue


tsList = []
tsExpList = []

messages = 0
cnt_plan = 0
cnt_send = 0
cnt_recv = 0
        
def input_thread(L):
    raw_input()
    L.append(None)
    

class rec():
    cntcyc = 0
    firsttime = True
    dut = None
    
    def __init__(self, dut):
        self.cntcyc = 1
        self.dut = dut
        
        
    def receive(self, result):
        global cnt_recv        
        if self.firsttime:
            self.firsttime = False
            self.dut.log.info("***** Slave - Received Operations:")
            
        self.dut.log.debug("WBS Cycle #%3u, %3u Ops" % (self.cntcyc,len(result)))
        if self.cntcyc % 50 == 0:
                self.dut.log.info("%5u Cycles received" % self.cntcyc)   
        self.cntcyc += 1
        cnt = 0
        for op in result:
            dat = "      None"
            if op.dat is not None:
                dat = "0x%08x" % op.dat
            self.dut.log.debug( "#%3u ADR: 0x%08x DAT: %s IDLW: %3u SEL: 0x%x" % (cnt, op.adr, dat, op.idle, op.sel))
            cnt += 1
            cnt_recv += 1
            

@coroutine
def datagen(dut, wbm, messages):
    reslist = []
    idleGenWord     = genw.random_data(0, 5)    
    idleGenCyc      = genw.random_data(1, 10)
    idleGenBlock    = genw.random_data(1, 10)
    cntGenX1000     = genw.incrementing_data(0x1000, 0x1000)
    cntGen          = genw.incrementing_data(1, 1)
    adrGen          = genw.incrementing_data()
    #tsGen           = genw.random_data(0, 50, 64)
    tsGen           = genw.incrementing_data(1)
    clkedge = RisingEdge(dut.clk)
    global cnt_send
    
    for i in range(0, messages):
        opQ = Queue.Queue(8)
                
        ts = tsGen.next()
        tsExpList.append(ts)
        opQ.put(WBO(adrGen.next(), ts >> 32,          idleGenWord.next()))
        opQ.put(WBO(adrGen.next(), ts & 0xffffffff,   idleGenWord.next()))
        n = cntGenX1000.next()
        opQ.put(WBO(adrGen.next(), n + cntGen.next(), idleGenWord.next()))
        opQ.put(WBO(adrGen.next(), n + cntGen.next(), idleGenWord.next()))
        opQ.put(WBO(adrGen.next(), n + cntGen.next(), idleGenWord.next()))
        opQ.put(WBO(adrGen.next(), n + cntGen.next(), idleGenWord.next()))
        opQ.put(WBO(adrGen.next(), n + cntGen.next(), idleGenWord.next()))
        opQ.put(WBO(adrGen.next(), n + cntGen.next(), idleGenWord.next()))
        
        while not opQ.empty():
            dowords = random.randint(1, 8)
            cycle = []
            for i in range(dowords):
                if not opQ.empty():
                    cycle.append(opQ.get_nowait())
                    cnt_send += 1
            tmp = yield wbm.send_cycle(cycle)
            reslist.append(tmp)
            #wait a couple of clockcycle before next wb cycle
            for i in range(idleGenCyc.next()):
                yield clkedge
       
        #wait a couple of clockcycle before next block
        for i in range(idleGenBlock.next()):
            yield clkedge 

#    dut.log.info("***** Master - Received Replies:")
#    cyccnt = 0    
#    
#    for cycle in reslist:
#        dut.log.info("WBM Cycle #%3u, %3u Ops" % (cyccnt,len(cycle)))
#        cyccnt += 1
#        cnt = 0
#        for res in cycle:
#            dat = "      None"
#            if res.dat is not None:
#                dat = "0x%08x" % res.dat
#
#            ackerr = "ERR"                
#            if res.ack:
#                ackerr = "ACK"
#                
#            dut.log.debug("#%3u ACK/ERR: %s RD: %s IDLW: %3u STLW: %3u ACKW: %3u" % (cnt, ackerr, dat, res.waitidle, res.waitstall, res.waitack))
#            cnt += 1
         



        
@coroutine
def tscheck(dut):
    clkedge = RisingEdge(dut.clk)
    tsErrGen = genw.random_data(1, 9)    
    
    lastTsValid = False
    while True:
        if bool(dut.ts_valid_out.getvalue()) and not lastTsValid:
            if tsErrGen.next():            
                tsList.append(long(dut.ts_out.getvalue()))
            else:
                if not tsErrGen.next():
                    tsList.append(long(dut.ts_out.getvalue()) + 100)
                    
        lastTsValid = bool(dut.ts_valid_out.getvalue())
        yield clkedge


clkref_period = 8
clksys_period = 16

@cocotb.test()
def test_prio2(dut):
    global messages
    global cnt_plan

    ##### Test Global Parameters    
    messages = 20   
    cnt_plan = 8*messages 
    
    dut.log.setLevel(logging.INFO)
    
    #Setup Clocks
    cocotb.fork(Clock(dut.clk, clkref_period).start())
    cocotb.fork(Clock(dut.clk2, clksys_period).start())
    clkedge = RisingEdge(dut.clk)
    
    # Reset the DUT
    dut.log.debug("Resetting DUT")
    dut.reset_n     <= 0
    dut.reset_n2    <= 0
    dut.en_in       <= 0
    yield Timer(50*clksys_period)
    dut.log.debug("Out of reset")
    
    dut.reset_n     <= 1
    dut.reset_n2    <= 1
    yield Timer(50*clksys_period)
    
   #Timestamp capture routine. Save TSs to compare later against expected values    
    cocotb.fork(tscheck(dut))   
    
    #Data/Signal Generators for WB Slave
    replyWaitGen    = genw.random_data(1, 3)
    ackGen          = genw.random_data(0, 1)
    stallGen        = genb.bit_toggler(genw.random_data(0, 10), genw.random_data(1, 50))
    #Callback for WB SLave
    output = rec(dut)
    #instantiate WB Slave
    wbs  = WishboneSlave(entity=dut, name="wbm", clock=dut.clk, callback=output.receive, stallwaitgen=stallGen, replywaitgen=replyWaitGen)
    wbs.log.setLevel(logging.INFO)    
    
    #instantiate WB Master    
    wbm  = WishboneMaster(dut, "wbs", dut.clk, 500)
    wbm.log.setLevel(logging.INFO) 
    #Stimulus routine. Generate Cycles for WB Master 
    yield datagen(dut, wbm, messages)

    
    ##### TEST Evaluation ######
    
    #wait for all ops to finish
    cnt_timeout = cnt_plan*20
    while (cnt_timeout) and ((cnt_recv < cnt_plan) and (len(tsList) < len(tsExpList))):
        yield clkedge
        cnt_timeout -= 1
    
    #either timeout or all operations complete. Continue      
    yield Timer(50*clksys_period)
    print ""    
    print "%s%s" % (" "*117, "*"*40)
    print ""
    #check for timeout  
    if cnt_timeout <= 0:
        raise TestFailure("Timeout: Not all Operations made it through. Planned: %u Sent: %u Received: %u" % (cnt_plan, cnt_send, cnt_recv)) 
   
    #check if we got too many sent ops for some reason 
    if (cnt_send > cnt_plan):
        raise TestFailure("There were more replies than sent operations. Planned: %u Sent: %u Received: %u" % (cnt_plan, cnt_send, cnt_recv)) 
        
    #check if we got too replies many for some reason 
    if (cnt_recv > cnt_plan):
        raise TestFailure("There were more replies than sent operations. Planned: %u Sent: %u Received: %u" % (cnt_plan, cnt_send, cnt_recv)) 
    
    #check timestamps against expected values
    s = set(tsList)
    result = [x for x in tsExpList if x not in s]
    if len(result):
        raise TestFailure("Expected Timestamps missing from actual result: %s\n Expected: %s\n Got:      %s" % (result, tsExpList, tsList))                        
        
    #all okay, test passed
    print ("Expected Timestamps missing from actual result: %s\n Expected: %s\n Got:      %s" % (result, tsExpList, tsList))                        
        
    raise TestSuccess("All operations processed, all expected timestamps present.\nPlanned: %u Sent: %u Received: %u\nMessages: %u Timestamps: %u" % (cnt_plan, cnt_send, cnt_recv, output.cntcyc-1, messages - len(result)))
    print "*"*80

  #  L = []
   # thread.start_new_thread(input_thread, (L,))
  #  print "Press Any key to close"
  #  while True:
  #     if L: 
  #        print L
  #        break
  #     yield RisingEdge(dut.clk2)

    print "DONE *****"
       
   
    
    
        
