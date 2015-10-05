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
from cocotb.utils import hexdump
from cocotb.monitors import BusMonitor
from cocotb.triggers import RisingEdge, ReadOnly


def is_sequence(arg):
        return (not hasattr(arg, "strip") and
        hasattr(arg, "__getitem__") or
        hasattr(arg, "__iter__"))


class WishboneRes():
    dat = None
    ack = False
    waitstall = 0
    waitack = 0
    waitidle = 0
    
    def __init__(self, ack, dat, idles, stalled, waitack):
        self.ack        = ack        
        self.dat        = dat
        self.waitstall  = stalled
        self.waitack    = waitack
        self.waitidle   = idles
        
class WishboneOp():
    adr     = 0
    sel     = 0xf     
    dat     = 0
    idle    = 0
    
    def __init__(self, adr, dat=None, idle=0, sel=0xf):
        self.adr    = adr        
        self.dat    = dat
        self.sel    = sel
        self.idle   = idle
        
  

class Wishbone(BusMonitor):
    """Wishbone
    """
    _width = 32
    
    _signals = ["cyc", "stb", "we", "sel", "adr", "datwr", "datrd", "ack"]
    _optional_signals = ["err", "stall"]


    def __init__(self, entity, name, clock):
        BusMonitor.__init__(self, entity, name, clock)
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
    _acked_ops      = 0  # ack cntr. comp with opbuf len. wait for equality before releasing lock
    _res_buf        = [] # save readdata/ack/err
    _clk_cycle_count = 0
    _datGen         = None
    _errGen         = None
    _stallWaitGen   = None
    _replyWaitGen   = None
    _last_time      = 0

    def defaultGen(self):
        while True:        
            yield 0

    def __init__(self, entity, name, clock, datGen=None, errGen=None, replyWaitGen=None, stallWaitGen=None):
        Wishbone.__init__(self, entity, name, clock)
        self.log.info("Wishbone Slave created")
        self._replyWaitGen  = self.defaultGen 
        self._stallWaitGen  = self.defaultGen 
        self._datGen        = self.defaultGen 
        self._errGen        = self.defaultGen 
        if replyWaitGen != None:
            self._replyWaitGen  = replyWaitGen 
        if stallWaitGen != None:
            self._stallWaitGen  = stallWaitGen
        if errGen != None:
            self._errGen        = errGen 
        if datGen != None:
            self._datGen        = datGen    
        
             
  
    @coroutine
    def start_listen(self):
        if self.busy:
            yield self.busy_event.wait()
        self.busy_event.clear()
        self.busy       = True
        
        if hasattr(self.bus, "stall"):
            cocotb.fork(self._stall())
        cocotb.fork(self._clk_cycle_counter())         
        cocotb.fork(self._receive())        
        self.log.debug("Start listening...")

    @coroutine
    def stop_listen(self):
        self.busy = False
        self.busy_event.set()
        self.log.debug("Stop listening")
        yield RisingEdge(self.clock)   

    @coroutine 
    def _clk_cycle_counter(self):
        """
        """
        clkedge = RisingEdge(self.clock)
        self._clk_cycle_count = 0
        while self.busy:
            yield clkedge
            self._clk_cycle_count += 1

    @coroutine
    def _stall(self):
        clkedge = RisingEdge(self.clock)         
        while self.busy:
            stall = self._stallWaitGen.next()
            self.bus.stall.setimmediatevalue(stall)
            yield clkedge
        


    @coroutine
    def _respond(self):
        clkedge = RisingEdge(self.clock)        
        valid =  self.bus.cyc.getvalue() and self.bus.stb.getvalue()
        
        if valid:
            #if there is a stall signal, take it into account
            if hasattr(self.bus, "stall"):
                valid = valid and not self.bus.stall.getvalue()                 
            #wait before replying ?    
            reply = self._replyWaitGen.next()
                
            if reply != None:
                replycnt = reply
                while replycnt > 0:
                    replycnt -= 1            
                    yield clkedge     
                    
            #Response: rddata/don't care        
            if (not self.bus.we.getvalue()):
                dat = self._datGen.next()
            else:
                dat = 0
            self.bus.dat.setimmediatevalue(dat)
            
            #Response: ack/err
            if hasattr(self.bus, "err"):                
                err = self._errGen.next()
                self.bus.err.setimmediatevalue(err)
            else:
                err = 0
                
            self.bus.ack.setimmediatevalue(not err)
            
        
        yield clkedge
        
        # save operation
        datwr = None
        if self.bus.we.getvalue():
            datwr = self.bus.datwr.getvalue()
        
        idleTime = self._clk_cycle_count - self._lastTime  
        self._res_buf.append(WishboneOp(self.bus.adr.getvalue(), datwr, self.bus.sel.getvalue(), idleTime))
        self._lastTime = self._clk_cycle_count
        
        
        
    @coroutine
    def _receive(self):
        clkedge = RisingEdge(self.clock)
        lastCycle = 0       
        
        while self.busy:
            if lastCycle == 0 and self.bus.cyc.getvalue() == 1:
                self._res_buf = []
                
            self._respond(self)
            
            if lastCycle == 1 and self.bus.cyc.getvalue() == 0:
                self._recv(self._res_buf)
            yield clkedge
            
        self._recv(self._res_buf)     
            
        
        
        
        
