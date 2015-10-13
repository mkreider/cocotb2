# -*- coding: utf-8 -*-
"""
Created on Wed Oct  7 13:01:18 2015

@author: mkreider
"""

class WishboneAux():
    adr   = 0
    datwr = None     
    sel         = 0xf
    waitStall   = 0
    waitIdle    = 0
    ts          = 0
    
    def __init__(self, sel, adr, datwr, waitStall, waitIdle, tsStb):
        self.adr        = adr
        self.datwr      = datwr        
        self.sel        = sel
        self.waitStall  = waitStall
        self.ts         = tsStb
        self.waitIdle   = waitIdle

class WishboneRes():
    adr   = 0
    sel   = 0xf
    datwr = None    
    datrd = None
    ack = False
    waitstall = 0
    waitack = 0
    waitidle = 0
    
          
    
    def __init__(self, ack, sel, adr, datrd, datwr, waitIdle, waitStall, waitAck):
        self.ack        = ack
        self.sel        = sel
        self.adr        = adr
        self.datrd      = datrd
        self.datwr      = datwr
        self.waitStall  = waitStall
        self.waitAck    = waitAck
        self.waitIdle   = waitIdle
        
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
        
def is_sequence(arg):
        return (not hasattr(arg, "strip") and
        hasattr(arg, "__getitem__") or
        hasattr(arg, "__iter__"))

replyTypes = {1 : "ack", 2 : "err", 3 : "rty"}           