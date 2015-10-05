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
Drivers for Altera Avalon interfaces.

See http://www.altera.co.uk/literature/manual/mnl_avalon_spec.pdf

NB Currently we only support a very small subset of functionality
"""
import random

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import RisingEdge, Event
from cocotb.drivers import BusDriver
from cocotb.utils import hexdump
from cocotb.binary import BinaryValue
from cocotb.result import ReturnValue, TestError

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
        
  

class Wishbone(BusDriver):
    """Wishbone
    """
    _width = 32
    
    _signals = ["cyc", "stb", "we", "sel", "adr", "datwr", "datrd", "ack"]
    _optional_signals = ["err", "stall"]


    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)
        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.cyc.setimmediatevalue(0)
        self.bus.stb.setimmediatevalue(0)            
        self.bus.we.setimmediatevalue(0)
        self.bus.adr.setimmediatevalue(0)
        self.bus.datwr.setimmediatevalue(0)
        
        v = self.bus.sel.value
        v.binstr = "1" * len(self.bus.sel)
        self.bus.sel <= v
    
    def send_cycle(self, ops):
        pass

class WishboneMaster(Wishbone):
    """Wishbone master
    """
    _acked_ops      = 0  # ack cntr. comp with opbuf len. wait for equality before releasing lock
    _res_buf        = [] # save readdata/ack/err
    _op_buf         = [] # save read/write order
    _op_cnt         = 0 # number of ops we've been issued
    _clk_cycle_count = 0
    

    
    def __init__(self, entity, name, clock):
        Wishbone.__init__(self, entity, name, clock)
        self.log.info("Wishbone Master created")
        self.busy_event = Event("%s_busy" % name)
        self.busy = False
  
  
    @coroutine
    def _open_cycle(self):
        if self.busy:
            self.log.debug("This should not be busy !!!")
            yield self.busy_event.wait()
        self.busy_event.clear()
        self.busy       = True
        cocotb.fork(self._read())
        cocotb.fork(self._clk_cycle_counter()) 
        self.bus.cyc    <= 1
        self._acked_ops = 0  
        self._rd_buf    = [] 
        self._op_buf    = []
        self.log.debug("Opening cycle, %u Ops" % self._op_cnt)
        
    @coroutine    
    def _close_cycle(self):
        while self._acked_ops < self._op_cnt:
            self.log.debug("Waiting for missing acks: %u/%u" % (self._acked_ops, self._op_cnt) )
            yield RisingEdge(self.clock)
        self.busy = False
        self.busy_event.set()
        self.bus.cyc <= 0 
        self.log.debug("Closing cycle")
        yield RisingEdge(self.clock)        

    @coroutine
    def _wait_stall(self):
        """Wait for stall to be low before continuing
        """
        count = None
        if hasattr(self.bus, "stall"):
            count = 0            
            while self.bus.stall.getvalue():
                yield RisingEdge(self.clock)
                count += 1
            if count:
                self.log.debug("Stalled for %u cycles" % count)
        raise ReturnValue(count)
    
    @coroutine
    def _wait_ack(self):
        """Wait for ACK on the bus before continuing
        """
        count = None
        count = 0
        if not hasattr(self.bus, "stall"):
            while not self.bus.ack.getvalue():
                yield RisingEdge(self.clock)
                count += 1
            self.log.debug("Waiting %u cycles for ACK" % count)     
    
    @coroutine 
    def _read(self):
        """
        """
        count = 0
        clkedge = RisingEdge(self.clock)
        while self.busy:
            valid = self.bus.ack.getvalue()
            if hasattr(self.bus, "err"):
                valid = valid or self.bus.err.getvalue()     
            if(valid):
                self._acked_ops += 1
                [we, idle, stalled, ts] = self._op_buf[self._acked_ops-1]
                if(not we):
                    val = int(self.bus.datrd.getvalue())
                else:
                    val = None
                self._res_buf.append(WishboneRes(bool(self.bus.ack.getvalue()), val, idle, stalled, self._clk_cycle_count-ts))
            yield clkedge
            count += 1    

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
    def _drive(self, we, adr, dat, sel, idle):
        """
        Args:
            string (str): A string of bytes to send over the bus
        """
        # Avoid spurious object creation by recycling
        #print "Driver"
        clkedge = RisingEdge(self.clock)
        if self.busy:
            if idle != None:
                idlecnt = idle
                while idlecnt > 0:
                    idlecnt -= 1
                    yield clkedge
                
            self.bus.stb    <= 1
            self.bus.adr    <= adr
            self.bus.sel    <= sel
            self.bus.datwr  <= dat
            self.bus.we     <= we
            #deal with a current read (pipelined only)
            stalled = yield self._wait_stall()
            self._op_buf.append([we, idle, stalled, self._clk_cycle_count])
            yield clkedge
            
            #print self._op_buf
            self.bus.stb    <= 0
            # non pipelined
            yield self._wait_ack()
           
                
        else:
           self.log.error("Cannot drive bus outside cycle")


  
    @coroutine
    def send_cycle(self, arg):
        """
        Args:
            list(WishboneOp)
        """
        cnt = 0
        clkedge = RisingEdge(self.clock)
        yield clkedge
        if is_sequence(arg):
            if len(arg) < 1:
                self.log.error("List contains no operations to carry out")
            else:
         
                self._op_cnt = len(arg)
                firstword = True
                for op in arg:
                    if firstword:
                        firstword = False
                        yield self._open_cycle()
                    if op.dat != None:
                        we = 1
                    else:
                        we = 0
                    yield self._drive(we, op.adr, op.dat, op.sel, op.idle)
                    self.log.debug("#%3u WE: %s ADR: 0x%08x DAT: 0x%08x SEL: 0x%1x IDLE: %3u" % (cnt, we, op.adr, op.dat, op.sel, op.idle))
                    cnt += 1
                yield self._close_cycle()
            raise ReturnValue(self._res_buf)
        else:
            self.log.error("Expecting a list")

    
      