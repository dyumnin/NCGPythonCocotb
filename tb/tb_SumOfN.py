import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles
from cocotb_bus.monitors import BusMonitor
from cocotb_bus.drivers import BusDriver
from cocotb_bus.scoreboard import Scoreboard
from cocotb.binary import BinaryValue
from cocotb.regression import TestFactory
import random

import logging

random.seed(16)

class sumofNTB(object):
    def __init__(self, dut, ignore_interop = False):
        self.dut = dut
        self.ignore_interop = ignore_interop
        cocotb.fork(Clock(dut.CLK, 1, units="ns").start())

        self.put_stream = DataPutMonitor(dut, callback=self.sumofN_model)
        self.get_stream = DataGetMonitor(dut)
        self.intr_stream = IntrMonitor(dut)
        self.config_stream = ConfigurePortMonitor(dut, callback=self.config_model)

        self.put_stream_driver = DataPutDriver(dut)
        self.config_stream_driver = ConfigurePortDriver(dut)

        self.N = 0
        self.received_transactions = []
        self.expected_output = []
        self.expected_intr = []
        self.prev_output = 0
        self.start_op = 0

        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.get_stream, self.expected_output, strict_type=False)
        self.scoreboard.add_interface(self.intr_stream, self.expected_intr, strict_type=False)
        self.logger = logging.getLogger("cocotb_logger")
        self.logger.setLevel(logging.DEBUG)

    def sumofN_model(self, transaction):
        if self.put_stream.bus.EN_in_put.value and self.put_stream.bus.RDY_in_put.value and self.start_op:
            self.logger.debug("transaction: %s", transaction)
            self.received_transactions.append(transaction.buff)
            int_sum = sum([int.from_bytes(i, byteorder = "little") for i in self.received_transactions])
            self.expected_output.append(BinaryValue(self.prev_output, n_bits = len(self.put_stream.bus.in_put), bigEndian = True))
            if self.get_stream.bus.EN_out_get == 1 or self.ignore_interop == True:
                self.prev_output = int_sum
                self.logger.debug("Expected output: %s", self.expected_output)
        else:
            if self.put_stream.bus.EN_in_put.value == 1 and self.start_op == False:
                self.expected_intr.append(BinaryValue(1, n_bits=1, bigEndian=True))
            self.expected_output.append(BinaryValue(self.prev_output, n_bits = len(self.put_stream.bus.in_put), bigEndian = True))


    def config_model(self, transaction):
        if (int.from_bytes(transaction[0].buff, byteorder = "little") == 0) :
            self.N = transaction[1].buff
        elif (int.from_bytes(transaction[0].buff, byteorder = "little") == 1 and int.from_bytes(transaction[1].buff, byteorder = "little") == 1) :
            self.start_op = True
        else:
            self.start_op = False

    async def reset(self):
        self.dut.RST_N.setimmediatevalue(0)
        self.dut.EN_in_put.setimmediatevalue(0)
        self.dut.in_put.setimmediatevalue(0)
        self.dut.EN_out_get.setimmediatevalue(0)
        self.dut.EN_configure.setimmediatevalue(0)
        self.dut.configure_address.setimmediatevalue(0)
        self.dut.configure_data.setimmediatevalue(0)
        self.prev_output = 0
        await FallingEdge(self.dut.CLK)
        self.dut.RST_N <= 1

        
class DataPutMonitor(BusMonitor):
    _signals = ["in_put", "EN_in_put", "RDY_in_put"]

    def __init__(self, dut, callback=None, event=None):
        BusMonitor.__init__(self, dut, "", dut.CLK, callback = callback)

    async def _monitor_recv(self):
        clk_edge = RisingEdge(self.clock)
        while True:
            await clk_edge
            self._recv(self.bus.in_put.value)

class DataGetMonitor(BusMonitor):
    _signals = ["out_get", "EN_out_get", "RDY_out_get"]

    def __init__(self, dut, callback=None, event=None):
        BusMonitor.__init__(self, dut, "", dut.CLK)
        self.dut = dut

    async def _monitor_recv(self):
        clk_edge = RisingEdge(self.clock)
        while True:
            await clk_edge
            self._recv(self.bus.out_get.value)

class ConfigurePortMonitor(BusMonitor):
    _signals = ["configure_address", "configure_data", "EN_configure", "RDY_configure"]

    def __init__(self, dut, callback=None, event=None):
        BusMonitor.__init__(self, dut, "", dut.CLK, callback = callback)

    async def _monitor_recv(self):
        clk_edge = RisingEdge(self.clock)
        while True:
            await clk_edge
            if self.bus.RDY_configure.value == 1 and self.bus.EN_configure.value == 1:
                self._recv((self.bus.configure_address.value, self.bus.configure_data.value))

class IntrMonitor(BusMonitor):
    _signals = ["interrupt", "RDY_interrupt"]

    def __init__(self, dut, callback=None, event=None):
        BusMonitor.__init__(self, dut, "", dut.CLK)

    async def _monitor_recv(self):
        clk_edge = RisingEdge(self.clock)
        while True:
            await clk_edge
            if self.bus.RDY_interrupt.value:
                if self.bus.interrupt == 1:
                    self._recv(self.bus.interrupt.value)

class DataPutDriver(BusDriver):
    _signals = ["in_put", "EN_in_put", "RDY_in_put"]

    def __init__(self, dut, callback=None, event=None):
        BusDriver.__init__(self, dut, "", dut.CLK)
        self.bus.EN_in_put <= 0
        self.bus.in_put <= 0

    async def _driver_send(self, value, sync=True):
        clk_edge = RisingEdge(self.clock)
        data = BinaryValue(value["data"], n_bits=len(self.bus.in_put), bigEndian=False)
        en = BinaryValue(value["enable"], n_bits=1, bigEndian=False)
        await clk_edge
        if self.bus.RDY_in_put:
            self.bus.EN_in_put <= en
            self.bus.in_put <= data

class ConfigurePortDriver(BusDriver):
    _signals = ["configure_address", "configure_data", "EN_configure", "RDY_configure"]

    def __init__(self, dut, callback=None, event=None):
        BusDriver.__init__(self, dut, "", dut.CLK)
        self.bus.EN_configure <= 0
        self.bus.configure_address <= 0
        self.bus.configure_data <= 0

    async def _driver_send(self, value, sync=True):
        clk_edge = RisingEdge(self.clock)
        address = BinaryValue(value["config_addr"], n_bits=len(self.bus.configure_address), bigEndian=False)
        data = BinaryValue(value["config_data"], n_bits=len(self.bus.configure_data), bigEndian=False)
        en = BinaryValue(value["enable"], n_bits=1, bigEndian=False)
        await clk_edge
        if self.bus.RDY_configure:
            self.bus.EN_configure <= en
            self.bus.configure_data <= data
            self.bus.configure_address <= address

async def tb_fn(dut, N = 5, start_op = 1, ignore_interop = False):
    tb = sumofNTB(dut, ignore_interop)
    await tb.reset()
    config_N = {"config_addr" : 0, "config_data" : N, "enable" : 1}
    config_start = {"config_addr": 1, "config_data": 1, "enable": start_op}
    config_end = {"config_addr" : 1,  "config_data" : 1, "enable" : 0}
    await tb.config_stream_driver.send(config_N)
    await tb.config_stream_driver.send(config_start)
    await tb.config_stream_driver.send(config_end)

    test_data = [random.randint(0, 2 ** 8 - 1) for i in range(N)]
    for data in test_data:
        input = {"data" : data, "enable" : 1}
        await tb.put_stream_driver.send(input)   
    await tb.put_stream_driver.send(dict({"data": 0, "enable": 0}))
    dut.EN_out_get <= 1
    await ClockCycles(dut.CLK, num_cycles=1)
    raise tb.scoreboard.result

tf = TestFactory(test_function=tb_fn)
tf.add_option(('start_op', 'ignore_interop'), ([1, True], [1, False], [0, False]))
tf.generate_tests()


