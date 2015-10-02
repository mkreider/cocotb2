#!/usr/bin/env python


"""
    Collection of generators for creating word streams
"""
import random
from cocotb.decorators import public


@public
def get_words(nwords, generator):
    """Get nwords from generator"""
    result = ""
    for i in range(nwords):
        result += next(generator)
    return result



@public
def random_data(minval = 0, maxval = None, width = 32):
    """Random bytes"""
    bytes = (width + 7) // 8 
    if maxval == None:
        maxval = 2**width-1
    
    while True:
        yield (long(random.randint(minval, maxval)) >> (bytes * 8 - width))


@public
def incrementing_data( increment=4, start=0, width = 32):
    """Incrementing bytes"""
    bytes = (width + 7) // 8     
    val = start
    while True:
        val = val & 2**width-1        
        yield (long(val) >> (bytes * 8 - width))
        val += increment
        


@public
def repeating_words(pattern="\x00"):
    """Repeat a pattern of bytes"""
    while True:
        for word in pattern:
            yield word

