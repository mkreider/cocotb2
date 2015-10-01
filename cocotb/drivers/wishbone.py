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
from cocotb.triggers import RisingEdge, ReadOnly, Event
from cocotb.drivers import BusDriver
from cocotb.utils import hexdump
from cocotb.binary import BinaryValue
from cocotb.result import ReturnValue, TestError
from cocotb.decorators import public
from cocotb.generators.bit import bit_toggler

class WishboneOp():
    adr     = 0
    sel     = 0xf     
    we      = False
    dat     = 0 
    
    def __init__(self, adr, we=False, dat=0, sel=0xf):
        self.adr    = adr        
        if(we):        
            self.we = 1
        else:
            self.we = 0
        self.dat    = dat
        self.sel    = sel

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
    _idle           = True
    
    def idler(self, maximum=10, sigma=None):
        """Generator to intermittently insert a single cycle pulse
    
        Kwargs:
            max (int):     Max number of cycles in between single cycle gaps
    
            sigma (int):    Standard deviation of gaps.  mean/4 if sigma is None
        """
        while True:        
            mean = maximum/2
            if sigma is None:
                sigma = mean / 4.0
            val = random.gauss(mean, sigma)    
            if val > maximum:
                val = maximum
            yield(int(abs(val)))
    
    def __init__(self, entity, name, clock, maxidle=0, stddev=0):
        Wishbone.__init__(self, entity, name, clock)
        self.log.info("Wishbone Master created")
        self.busy_event = Event("%s_busy" % name)
        self.busy = False
        self.idle = self.idler(maxidle, stddev)

    def __len__(self):
        return 2**len(self.bus.adr)

    
        

    @coroutine
    def _open_cycle(self):
        print "Opening"
        if self.busy:
            yield self.busy_event.wait()
        self.busy_event.clear()
        self.busy       = True
        cocotb.fork(self._read()) 
        self.bus.cyc    <= 1
        self._acked_ops = 0  
        self._rd_buf    = [] 
        self._op_buf    = []
        self.log.debug("Opening cycle, %u Ops" % self._op_cnt)
        
    @coroutine    
    def _close_cycle(self):
        #print "Closing Ops: %u Ackops: %u" % (self._op_cnt, self._acked_ops)
        while self._acked_ops < self._op_cnt:
            #print "Waiting: Ops: %u Ackops: %u" % (len(self._op_buf), self._acked_ops)
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
        count = 0
        if hasattr(self.bus, "stall"):
            while self.bus.stall.getvalue():
                yield RisingEdge(self.clock)
                count += 1
            if count:
                self.log.debug("Stalled for %u cycles" % count) 
    
    @coroutine
    def _wait_ack(self):
        """Wait for ACK on the bus before continuing
        """
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
            #print "Reader"
           # print "ack: %u err: %u stb: %u cnt: %u" % (self.bus.ack.getvalue(), self.bus.err.getvalue(), self.bus.stb.getvalue(), count)
            if(self.bus.ack.getvalue() or self.bus.err.getvalue()):
                self._acked_ops += 1
                #print self._op_buf                
                #print "Ops: %u Ackops: %u" % (len(self._op_buf), self._acked_ops)                
                if(not self._op_buf[self._acked_ops-1]):
                    val = int(self.bus.datrd.getvalue())
                else:
                    val = None
                    #print "Saving. Ops: %u Ackops: %u We %u Val %x" % (len(self._op_buf), self._acked_ops,  self._op_buf[self._acked_ops-1], self.bus.datrd.getvalue())
                self._res_buf.append([val , int(self.bus.ack.getvalue())] )
            yield clkedge
            count += 1

    @coroutine
    def _drive(self, op):
        """
        Args:
            string (str): A string of bytes to send over the bus
        """
        # Avoid spurious object creation by recycling
        #print "Driver"
        clkedge = RisingEdge(self.clock)
        if self.busy:
            idle = self.idle.next()
            if idle > 0 and self._idle:
                self.log.debug("Idling for %u cycles" % idle) 
                while idle > 0:
                    idle -= 1
                    yield clkedge
                
            self.bus.stb    <= 1
            self.bus.adr    <= op.adr            
            self.bus.sel    <= op.sel
            self.bus.datwr  <= op.dat
            self.bus.we     <= op.we
            #deal with a current read (pipelined only)
            yield self._wait_stall()
            self._op_buf.append(op.we)
            yield clkedge
            
            #print self._op_buf
            self.bus.stb    <= 0
            # non pipelined
            yield self._wait_ack()
           
                
        else:
           self.log.error("Cannot drive bus outside cycle")

    
    @coroutine
    def send_cycle(self, ops, idle=True):
        """
        Args:
            string (str): A string of bytes to send over the bus
        """
        # Avoid spurious object creation by recycling
        if len(ops) < 1:
            self.log.error("You gave me no operations to carry out")
        else:        
            self._op_cnt = len(ops)
            self._idle = idle
            firstword = True
            
            for op in ops:
                if firstword:
                    yield self._open_cycle()
                    firstword = False
                yield self._drive(op)
            yield self._close_cycle()
            #print self._rd_buf
        raise ReturnValue(self._res_buf)
        

    
      