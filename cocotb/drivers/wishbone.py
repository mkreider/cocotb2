

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import RisingEdge, Event
from cocotb.drivers import BusDriver
from cocotb.result import ReturnValue, TestFailure
from cocotb.wishbone_aux import WishboneAux as wba
from cocotb.wishbone_aux import WishboneRes as wbr
from cocotb.wishbone_aux import is_sequence     
  

class Wishbone(BusDriver):
    """Wishbone
    """
    _width = 32
    
    _signals = ["cyc", "stb", "we", "sel", "adr", "datwr", "datrd", "ack"]
    _optional_signals = ["err", "stall", "rty"]


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
    _acked_ops          = 0  # ack cntr. comp with opbuf len. wait for equality before releasing lock
    _res_buf            = [] # save readdata/ack/err
    _aux_buf            = [] # save read/write order
    _op_cnt             = 0 # number of ops we've been issued
    _clk_cycle_count    = 0
    _timeout            = None

    
    def __init__(self, entity, name, clock, timeout=5000):
        Wishbone.__init__(self, entity, name, clock)
        sTo = ", no cycle timeout"        
        if not (timeout is None):
            sTo = ", cycle timeout is %u clockcycles" % timeout
        self.log.info("Wishbone Master created%s" % sTo)
        self.busy_event = Event("%s_busy" % name)
        self.busy = False
        self._timeout = timeout
        
    @coroutine 
    def _clk_cycle_counter(self):
        """
            Cycle counter to time bus operations
        """
        clkedge = RisingEdge(self.clock)
        self._clk_cycle_count = 0
        while self.busy:
            yield clkedge
            self._clk_cycle_count += 1    
  
    @coroutine
    def _open_cycle(self):
        #Open new wishbone cycle        
        if self.busy:
            self.log.error("Opening Cycle, but WB Driver is already busy. Someting's wrong")
            yield self.busy_event.wait()
        self.busy_event.clear()
        self.busy       = True
        cocotb.fork(self._read())
        cocotb.fork(self._clk_cycle_counter()) 
        self.bus.cyc    <= 1
        self._acked_ops = 0  
        self._res_buf   = [] 
        self._aux_buf   = []
        self.log.debug("Opening cycle, %u Ops" % self._op_cnt)
        
    @coroutine    
    def _close_cycle(self):
        #Close current wishbone cycle  
        clkedge = RisingEdge(self.clock)
        count           = 0
        last_acked_ops  = 0
        #Wait for all Operations being acknowledged by the slave before lowering the cycle line
        #This is not mandatory by the bus standard, but a crossbar might send acks to the wrong master
        #if we don't wait. We don't want to risk that, it could hang the bus
        while self._acked_ops < self._op_cnt:
            if last_acked_ops != self._acked_ops:
                self.log.debug("Waiting for missing acks: %u/%u" % (self._acked_ops, self._op_cnt) )
            last_acked_ops = self._acked_ops    
            #check for timeout when finishing the cycle            
            count += 1
            if (not (self._timeout is None)):
                if (count > self._timeout): 
                    raise TestFailure("Timeout of %u clock cycles reached when waiting for reply from slave" % self._timeout)                
            yield clkedge
            
        self.busy = False
        self.busy_event.set()
        self.bus.cyc <= 0 
        self.log.debug("Closing cycle")
        yield clkedge        

    
    @coroutine
    def _wait_stall(self):
        """Wait for stall to be low before continuing
        """
        clkedge = RisingEdge(self.clock)
        count = 0
        if hasattr(self.bus, "stall"):
            count = 0            
            while self.bus.stall.getvalue():
                yield clkedge
                count += 1
                if (not (self._timeout is None)):
                    if (count > self._timeout): 
                        raise TestFailure("Timeout of %u clock cycles reached when on stall from slave" % self._timeout)                
            self.log.debug("Stalled for %u cycles" % count)
        raise ReturnValue(count)
    
    
    @coroutine
    def _wait_ack(self):
        """Wait for ACK on the bus before continuing
        """
        #wait for acknownledgement before continuing - Classic Wishbone without pipelining
        clkedge = RisingEdge(self.clock)
        count = 0
        if not hasattr(self.bus, "stall"):
            while not self.is_reply_valid():
                yield clkedge
                count += 1
            self.log.debug("Waited %u cycles for ackknowledge" % count)
        raise ReturnValue(count)    
    
    
    def is_reply_valid(self):
        #helper function for slave acks            
        valid = bool(self.bus.ack.getvalue())
        if hasattr(self.bus, "err"):
            valid = valid or bool(self.bus.err.getvalue())
        if hasattr(self.bus, "rty"):
            valid = valid or bool(self.bus.rty.getvalue())    
        return valid 
        
    
    @coroutine 
    def _read(self):
        """
            Reader for slave replies
        """
        count = 0
        clkedge = RisingEdge(self.clock)
        while self.busy:
            if(self.is_reply_valid()):
                val = int(self.bus.datrd.getvalue())
                #append reply and meta info to result buffer
                self._res_buf.append(wbr(bool(self.bus.ack.getvalue()), val, None, None, self._clk_cycle_count))
                self._acked_ops += 1
            yield clkedge
            count += 1    

    
    @coroutine
    def _drive(self, we, adr, dat, sel, idle):
        """
            Drive the Wishbone Master Out Lines
        """
    
        clkedge = RisingEdge(self.clock)
        if self.busy:
            # insert requested idle cycles            
            if idle != None:
                idlecnt = idle
                while idlecnt > 0:
                    idlecnt -= 1
                    yield clkedge
            # drive outputs    
            self.bus.stb    <= 1
            self.bus.adr    <= adr
            self.bus.sel    <= sel
            self.bus.datwr  <= dat
            self.bus.we     <= we
            yield clkedge
            #deal with flow control (pipelined wishbone)
            stalled = yield self._wait_stall()
            #append operation and meta info to auxiliary buffer
            self._aux_buf.append(wba(we, sel, stalled, idle, self._clk_cycle_count))
            #reset strobe and write enable without advancing time
            self.bus.stb    <= 0
            self.bus.we     <= 0
            # non pipelined wishbone
            yield self._wait_ack()
        else:
           self.log.error("Cannot drive the Wishbone bus outside a cycle!")


  
    @coroutine
    def send_cycle(self, arg):
        """
            The main sending routine        
        
        Args:
            list(WishboneOperations)
            
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
                        result = []
                        yield self._open_cycle()
                        
                    if op.dat != None:
                        we  = 1
                        dat = op.dat
                    else:
                        we  = 0
                        dat = 0
                    yield self._drive(we, op.adr, dat, op.sel, op.idle)
                    self.log.debug("#%3u WE: %s ADR: 0x%08x DAT: 0x%08x SEL: 0x%1x IDLE: %3u" % (cnt, we, op.adr, dat, op.sel, op.idle))
                    cnt += 1
                yield self._close_cycle()
                
                #do pick and mix from result- and auxiliary buffer so we get all meta info
                for res, op in zip(self._res_buf, self._aux_buf):
                    val = res.dat
                    if op.we:
                        val = None
                    result.append(wbr(res.ack, val, op.waitidle, op.waitstall, res.waitack-op.ts))
                
            raise ReturnValue(result)
        else:
            self.log.error("Expecting a list")
            raise ReturnValue(None)    
    
      