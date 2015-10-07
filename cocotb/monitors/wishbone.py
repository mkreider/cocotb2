''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
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
"""
Monitors for Altera Avalon interfaces.

See http://www.altera.co.uk/literature/manual/mnl_avalon_spec.pdf

NB Currently we only support a very small subset of functionality
"""
import cocotb
from cocotb.decorators import coroutine
from cocotb.monitors import BusMonitor
from cocotb.triggers import RisingEdge
from cocotb import wishbone_aux as wba


def is_sequence(arg):
        return (not hasattr(arg, "strip") and
        hasattr(arg, "__getitem__") or
        hasattr(arg, "__iter__"))


class Wishbone(BusMonitor):
    """Wishbone
    """
    _width = 32
    
    _signals = ["cyc", "stb", "we", "sel", "adr", "datwr", "datrd", "ack"]
    _optional_signals = ["err", "stall"]


    def __init__(self, *args, **kwargs):
        BusMonitor.__init__(self, *args, **kwargs)
        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.ack.setimmediatevalue(0)
        self.bus.datrd.setimmediatevalue(0)
        if hasattr(self.bus, "err"):        
            self.bus.err.setimmediatevalue(0)
        if hasattr(self.bus, "stall"): 
            self.bus.stall.setimmediatevalue(0) 
    
    @coroutine
    def _respond(self):
        pass
    
    @coroutine
    def receive_cycle(self, arg):
        pass
            

class WishboneSlave(Wishbone):
    """Wishbone slave
    """
    
    def bitSeqGen(self, tupleGen):
        while True: 
            [highCnt, lowCnt] = tupleGen.next()
                #make sure there's something in here            
            if lowCnt < 1:
                lowCnt = 1
            bits=[]
            for i in range(0, highCnt):
               bits.append(1)          
            for i in range(0, lowCnt):
               bits.append(0)
            for bit in bits:
                yield bit
    
    
    def defaultTupleGen():
        while True:        
            yield int(0), int(1)      
    
    def defaultGen():
        while True:        
            yield int(0)   
    
    _acked_ops      = 0  # ack cntr. comp with opbuf len. wait for equality before releasing lock
    _op_buf         = [] # save datwr, sel, idle
    _res_buf        = [] # save readdata/ack/err
    _clk_cycle_count = 0
    _cycle = False
    _datGen         = defaultGen()
    _errGen         = defaultGen()
    _stallWaitGen   = defaultGen()
    _replyWaitGen   = defaultGen()
    _lastTime      = 0

    

    def __init__(self, *args, **kwargs):
        datGen = kwargs.pop('datgen', None)
        errGen = kwargs.pop('errgen', None)
        replyWaitGen = kwargs.pop('replywaitgen', None)
        stallWaitGen = kwargs.pop('stallwaitgen', None)
        Wishbone.__init__(self, *args, **kwargs)
        cocotb.fork(self._stall())
        cocotb.fork(self._clk_cycle_counter())
        cocotb.fork(self._ack())
        self.log.info("Wishbone Slave created")
        
        if replyWaitGen != None:
            self._replyWaitGen  = replyWaitGen 
        if stallWaitGen != None:
            self._stallWaitGen  = self.bitSeqGen(stallWaitGen)
        if errGen != None:
            self._errGen        = self.bitSeqGen(errGen)
        if datGen != None:
            self._datGen        = datGen
        
    
    @coroutine 
    def _clk_cycle_counter(self):
        """
        """
        clkedge = RisingEdge(self.clock)
        self._clk_cycle_count = 0
        while True:
            if self._cycle:
                self._clk_cycle_count += 1
            else:
                self._clk_cycle_count = 0
            yield clkedge
            

    @coroutine
    def _stall(self):
        clkedge = RisingEdge(self.clock)         
        while True:
            if hasattr(self.bus, "stall"):
                self.bus.stall <= self._stallWaitGen.next()
            yield clkedge
            
        
    @coroutine
    def _ack(self):
        clkedge = RisingEdge(self.clock)         
        while True:        
            self.bus.ack    <= 0
            self.bus.datrd  <= 0
            if hasattr(self.bus, "err"):
                self.bus.err <= 0
            
            if len(self._res_buf):
                e = self._res_buf.pop()
                if e.waitack != None:
                    self.log.debug("AckDelay: %u" % e.waitack)
                    waitcnt = e.waitack
                    while waitcnt > 0:
                        waitcnt -= 1
                        yield clkedge
                self.bus.ack    <= int(e.ack)
                self.bus.datrd  <= e.dat
                if hasattr(self.bus, "err"):
                    self.bus.err    <= int(not e.ack)
            yield clkedge



    def _respond(self):
        valid =  bool(self.bus.cyc.getvalue()) and bool(self.bus.stb.getvalue())
        if hasattr(self.bus, "stall"):
                valid = valid and not bool(self.bus.stall.getvalue())
        
        if valid:
            #if there is a stall signal, take it into account
            #wait before replying ?    
            reply = self._replyWaitGen.next()
            #Response: rddata/don't care        
            if (not self.bus.we.getvalue()):
                dat = self._datGen.next()
            else:
                dat = 0
         
            #Response: ack/err
            if hasattr(self.bus, "err"):                
                err = self._errGen.next()
                print "ERRGEN: %u" % err
            else:
                err = 0
            #we can't do it now, they might be delayed. add to result buffer
            self._res_buf.append(wba.WishboneRes((not bool(err)), dat, 0, 0, reply))
            datwr = None
            if self.bus.we.getvalue():
                datwr = self.bus.datwr.getvalue()
            #get the time the master idled since the last operation
            #TODO: subtract our own stalltime or, if we're not pipelined, time since last ack
            idleTime = self._clk_cycle_count - self._lastTime -1
            op = wba.WishboneOp(self.bus.adr.getvalue(), datwr, idleTime, self.bus.sel.getvalue())
            self._lastTime = self._clk_cycle_count
            self._op_buf.append(op)
            

    @coroutine
    def _monitor_recv(self):
        clkedge = RisingEdge(self.clock)
  

        while True:
            if int(self._cycle) < int(self.bus.cyc.getvalue()):
                self._lastTime = self._clk_cycle_count -1
                
            self._respond()
            if int(self._cycle) > int(self.bus.cyc.getvalue()):
                self._recv(self._op_buf)
                self._op_buf = []
             
            self._cycle = self.bus.cyc.getvalue()
            yield clkedge