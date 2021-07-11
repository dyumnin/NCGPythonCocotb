import cocotb
from cocotb.triggers import FallingEdge, RisingEdge
from cocotb.clock import Clock
from cocotb_bus.monitors import BusMonitor
from cocotb_bus.drivers import BusDriver
from cocotb.scoreboard import Scoreboard
from cocotb.binary import BinaryValue
from cocotb.regression import TestFactory

import logging
import random

class SumN_tb():
    def __init__(self,dut, input_test = False,config_addr_test=False):
        self.dut = dut
        self.input_test = input_test
        self.config_addr_test = config_addr_test
        
        
        cocotb.fork(Clock(dut.CLK, 1, units="ns").start())
        
        self.input_stream = InPutDriv(dut)
        self.config_stream = ConfigDriv(dut)

        self.input_stream_recv = InPutMntr(dut, callback=self.model)
        self.output_stream_recv = OutGetMntr(dut)
        self.intr_stream_recv = Intr_Mntr(dut, callback=self.intr_model)
        self.config_stream_recv = ConfigMntr(dut, callback=self.config_model)

        self.expected_output = []
        self.expected_intr = []
        self.received_transactions = []
        self.N = 0
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.output_stream_recv,self.expected_output)
        self.scoreboard.add_interface(self.intr_stream_recv,self.expected_intr)
        self.log = logging.getLogger("cocotb_tb_log")
        self.log.setLevel(logging.DEBUG)

    def config_model(self,transaction):
        if (int.from_bytes(transaction[0].buff)==0):
            self.N <= transaction[1].buff
            self.dut._log.info("Config Model")
    
    def intr_model(self,transaction):
        if (self.config_addr_test == True):
            self.expected_intr.append(transaction)
            self.dut._log.info("interrupt model %d"%transaction)
    
    def model(self,transaction):
        self.log.debug("Transaction")
        self.received_transactions.append(transaction)
        self.pkts_sent +=1
        sum_model = BinaryValue(sum([int.from_bytes(i,byteorder='little') for i in self.received_transactions]),n_bits=len(self.input_stream.bus.in_put),bigEndian=False)
        self.expected_output.append(sum_model)
        if (self.pkts_sent.value == self.N.value):
            self.log.debug("number of inputs required %d but received %d"%(self.N.value,self.pkts_sent))      
        self.log.debug("Expected Output = %d"% self.expected_output.value)

    async def reset(self):
        self.log.debug("Resetting DUT")
        self.dut.RST_N.setimmediatevalue(0)
        self.dut.EN_in_put.setimmediatevalue(0)
        self.dut.in_put.setimmediatevalue(0)
        self.dut.EN_out_get.setimmediatevalue(0)
        self.dut.EN_configure.setimmediatevalue(0)
        self.dut.configure_address.setimmediatevalue(0)
        self.dut.configure_data.setimmediatevalue(0)
        await FallingEdge(self.dut.CLK)
        self.dut.RST_N <= 1

class InPutDriv(BusDriver):
    _signals = ["EN_in_put","in_put","RDY_in_put"]

    def __init__(self, dut, callback=None):
        BusDriver.__init__(self, dut,"",dut.CLK)
        self.bus.in_put <= 0
        self.bus.EN_in_put <= 0

    async def _driver_send(self, transaction, sync = True):
        await RisingEdge(self.clock)
        if self.bus.RDY_in_put:
            self.bus.in_put <= BinaryValue(transaction["data"],n_bits=len(self.bus.in_put),bigEndian=False)
            self.bus.EN_in_put <= BinaryValue(transaction["enable"],n_bits=1,bigEndian=False)

class ConfigDriv(BusDriver):
    _signals = ["EN_configure","configure_address","configure_data","RDY_configure"]

    def __init__(self, dut, callback=None):
        BusDriver.__init__(self, dut,"",dut.CLK)
        self.bus.configure_address <= 0
        self.bus.configure_data <= 0
        self.bus.EN_configure <= 0

    async def _driver_send(self, transaction, sync=True):
        await RisingEdge(self.clock)
        if self.bus.RDY_configure:
            self.bus.configure_address <= BinaryValue(transaction["config_address"],n_bits=len(self.bus.configure_address),bigEndian=False)
            self.bus.EN_configure <= BinaryValue(transaction["config_enable"],n_bits=1,bigEndian=False)
            self.bus.configure_data <= BinaryValue(transaction["config_data"],n_bits=len(self.bus.configure_data),bigEndian=False)

class InPutMntr(BusMonitor):
    _signals = ["RDY_in_put","EN_in_put","in_put"]

    def __init__(self, dut, callback=None):
        BusMonitor.__init__(self,dut,"",dut.CLK)                              

    async def _monitor_recv(self):
        await RisingEdge(self.clock)
        if self.bus.EN_in_put.value == 1 and self.bus.RDY_in_put.value == 1:
            self._recv(self.bus.in_put.value)

class OutGetMntr(BusMonitor):
    _signals = ["RDY_out_get","EN_out_get","out_get"]

    def __init__(self, dut, callback=None):
        BusMonitor.__init__(self,dut,"",dut.CLK)                              
    
    async def _monitor_recv(self):
        await RisingEdge(self.clock)
        if self.bus.EN_out_get.value == 1 and self.bus.RDY_out_get.value == 1:
            self._recv(self.bus.out_get.value)


class ConfigMntr(BusMonitor):
    _signals = ["RDY_configure","EN_configure","configure_address","configure_data"]

    def __init__(self, dut, callback=None):
        BusMonitor.__init__(self,dut,"",dut.CLK)                              
    
    async def _monitor_recv(self):
        await RisingEdge(self.clock)
        if self.bus.RDY_configure.value == 1 and self.bus.EN_configure.value == 1:
            self._recv(self.bus.configure_address.value,self.bus.configure_data.value)

class Intr_Mntr(BusMonitor):
    _signals = ["RDY_interrupt","interrupt"]

    def __init__(self, dut, callback=None):
        BusMonitor.__init__(self,dut,"",dut.CLK)                              

    async def _monitor_recv(self):
        await RisingEdge(self.clock)
        if self.bus.RDY_interrupt.value:
            if self.bus.interrupt == 1:
                self._recv(self.bus.interrupt.value)


async def test_sum_n(dut, N = 4, input_test = False, config_addr_test=False):
    tb=SumN_tb(dut, input_test, config_addr_test)
    await tb.reset()
    exp_sum = 0
    config_N = {"config_enable":1,"config_address":0,"config_data":N}
    if config_addr_test is True:
        config_start = {"config_enable":1,"config_address":0,"config_data":1}
    else:
        config_start = {"config_enable":1,"config_address":1,"config_data":1}
    config_end = {"config_enable":0,"config_address":1,"config_data":1}
    await tb.config_stream.send(config_N)
    await tb.config_stream.send(config_start)
    await tb.config_stream.send(config_end)
    pkts_recvd = 0
    #test_data = [random.randint(0,2**8-1)for i in range(N)]
    test_data = [5,4,2,1]
    if input_test is True:
        for i in range(N-1):
            in_put_data = {"enable" : 1,"data":test_data[i]}
            await tb.input_stream.send(in_put_data)
            pkts_recvd += 1
            exp_sum += test_data[i]
        dut._log.info('Required inputs %d but received %d. Interrupt value = %d'%(N,pkts_recvd,dut.interrupt.value))      
    elif config_addr_test is True:
        for i in range(N):
            in_put_data = {"enable" : 1,"data":test_data[i]}
            await tb.input_stream.send(in_put_data)
        exp_sum = BinaryValue(0,n_bits = 8,bigEndian=False)
        dut._log.info("Interrupt Value = %d"% dut.interrupt.value) 
    else : 
        for i in range(N):
            in_put_data = {"enable" : 1,"data":test_data[i]}
            await tb.input_stream.send(in_put_data)
            exp_sum += test_data[i]
        dut._log.info("Interrupt Value = %d"% dut.interrupt.value)
        
    await tb.input_stream.send(dict({"enable":0,"data":0}))
    dut.EN_out_get <= 1
    await RisingEdge(dut.CLK)
    if input_test is True:
        if dut.RDY_out_get.value == 0 :
            dut._log.info('Expected Sum Output value = 0. Sum Ready value = %d'%dut.RDY_out_get.value)
        dut._log.info("Sum Value = %d"% dut.out_get.value) 
        assert exp_sum == dut.out_get.value, 'Test Fail'
        dut._log.info("Test Pass")
    elif config_addr_test == True:
        dut._log.info("Detected Wrong Configuration Address")
        dut._log.info("Sum Value = %d"% dut.out_get.value) 
        assert exp_sum == dut.out_get.value, 'Test Fail'
        dut._log.info("Test Pass")
    else:
        dut._log.info("Sum Value = %d"% dut.out_get.value) 
        assert exp_sum == dut.out_get.value, 'Test Fail'
        dut._log.info("Test Pass")
    
    dut.EN_out_get <= 0
    await RisingEdge(dut.CLK)
    raise tb.scoreboard.result
    

tf = TestFactory(test_sum_n)
tf.add_option(('input_test','config_addr_test'), ([False, False], [False, True],[True, False]))
tf.generate_tests()

