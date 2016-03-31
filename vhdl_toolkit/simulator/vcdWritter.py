
from functools import wraps
from datetime import datetime
import sys
from vhdl_toolkit.hdlObjects.typeDefs import BIT
from vhdl_toolkit.synthetisator.rtlLevel.signal import Signal
from vhdl_toolkit.hdlObjects.typeShortcuts import vecT, hBit, vec
from vhdl_toolkit.synthetisator.vhdlSerializer import VhdlSerializer

def dumpMethod(func):
    """decorator which takes functions return and write it as line to dumpFile"""
    @wraps(func)
    def wrapped(*args, **kwrds):
        s = func(*args, **kwrds)
        if s is not None:
            self = args[0]
            self.dumpFile.write(s + '\n')
    return wrapped

class VcdVarInfo():
    """Info about signal registered in vcd"""
    def __init__(self, _id, dtype):
        self.width = 1 if dtype == BIT else dtype.getBitCnt()
        self.id = _id
        self.dtype = dtype

class VcdVarContext(dict):
    """Map of signals registered in this unit"""
    def __init__(self):
        super(VcdVarContext, self).__init__()
        self.nextId = 0
        self.idChars = [ chr(i) for i in range(ord("!"), ord("~") + 2) ]
        self.idCharsCnt = len(self.idChars)
        
    def idToStr(self, x):
        if x < 0: sign = -1
        elif x == 0: return self.idChars[0]
        else: sign = 1
        x *= sign
        digits = []
        while x:
            digits.append(self.idChars[x % self.idCharsCnt])
            x //= self.idCharsCnt
        if sign < 0:
            digits.append('-')
        digits.reverse()
        return ''.join(digits)
    
    def register(self, var):
        var_id = self.idToStr(self.nextId)
        if var in self:
            raise KeyError("%s is already registered" % (repr(var)))
        vInf = VcdVarInfo(var_id, var.dtype)
        self[var] = vInf 
        self.nextId += 1
        return vInf
    
class VcdModule():
    """Vcd module - container for variables"""
    def __init__(self, dumpFile, _vars, name):
        self.name = name
        self.dumpFile = dumpFile
        self.vars = _vars
    
    def __enter__(self):
        self.header()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.footer()
        
    @dumpMethod
    def header(self):
        return "$scope module %s $end" % self.name


    @dumpMethod    
    def var(self, sig):
        vInf = self.vars.register(sig)
        return "$var wire %d %s %s $end" % (vInf.width, vInf.id, sig.name) 

    @dumpMethod
    def footer(self):
        return "$upscope $end"

class VcdWritter():
    def __init__(self, dumpFile=sys.stdout):
        self.dumpFile = dumpFile
        self.vars = VcdVarContext()
        self.lastTime = -1
    
    @dumpMethod
    def date(self, text):
        return "$date\n   %s\n$end" % text
    
    @dumpMethod
    def version(self, text):
        return "$version   \n%s\n$end" % text
    
    @dumpMethod
    def timescale(self, picoSeconds):
        return "$timescale %dps $end" % picoSeconds
    
    def module(self, name):
        return VcdModule(self.dumpFile, self.vars, name)
    
    @dumpMethod
    def enddefinitions(self):
        return "$enddefinitions $end"
    
    @dumpMethod
    def setTime(self, t):
        lt = self.lastTime
        if  lt == t:
            return
        elif lt < t:
            self.lastTime = t
            return "#%d" % (t)
        else:
            raise Exception("VcdWritter invalid time update %d -> %d" % (lt, t))
        
    
    @dumpMethod
    def change(self, time, sig, newVal):
        self.setTime(time)
        varInfo = self.vars[sig]
        val = VhdlSerializer.BitString_binary(newVal.val, varInfo.width, newVal.vldMask)
        val = val.replace('"', "")
         
        if varInfo.dtype == BIT:
            frmt = "%s%s"
        else:
            frmt = "b%s %s" 
            
        return frmt % (val, varInfo.id)
    
if __name__ == "__main__":
    
    log = VcdWritter()
    log.date(datetime.now())
    with log.module("module0") as m:
        s1 = Signal('s1', BIT)
        s2 = Signal('s2', vecT(3))
        m.var(s1)
        m.var(s2)
    log.enddefinitions()
    log.change(0, s1, hBit(0))
    log.change(10000, s2, vec(0, 3))
    log.change(10000, s1, hBit(1))
    log.change(20000, s1, hBit(0))
    
    
    