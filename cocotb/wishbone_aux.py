# -*- coding: utf-8 -*-
"""
Created on Wed Oct  7 13:01:18 2015

@author: mkreider
"""

class WishboneAux():
    we          = False
    sel         = 0xf
    waitstall   = 0
    waitidle    = 0
    ts          = 0
    
    def __init__(self, we, sel, waitStall, waitIdle, tsStb):
        self.we         = we        
        self.sel        = sel
        self.waitstall  = waitStall
        self.ts       = tsStb
        self.waitidle   = waitIdle

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
        
def is_sequence(arg):
        return (not hasattr(arg, "strip") and
        hasattr(arg, "__getitem__") or
        hasattr(arg, "__iter__"))

replyTypes = {0 : "ack", 1 : "err", 2 : "rty"}           