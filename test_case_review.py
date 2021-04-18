# Code your testbench here
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly, Lock, Timer
from cocotb.scoreboard import Scoreboard
from cocotb.drivers import BusDriver
from cocotb.monitors import BusMonitor
from cocotb.regression import TestFactory
import random
import warnings

DATA_WIDTH = 8

@cocotb.coroutine
def test_N(dut):
    yield Timer(20,'ns')
    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    configure_data = int(dut.configure_data.value)
    dut._log.info('Detected DATA_WIDTH = %d, configure_data = %d' %
                  (DATA_WIDTH, configure_data))

    cocotb.fork(Clock(dut.CLK, 10, units='ns').start())

    dut.RST_N <= 0
    dut.EN_configure<=0
    dut.configure_address<=0
    
    for i in range(configure_data):
        dut.in_put[i] <= 0
    dut.EN_in_put <= 0
    dut.EN_out_get<=0
    yield FallingEdge(dut.CLK)
    yield FallingEdge(dut.CLK)
    dut.RST_N <= 1
    dut.EN_configure<=1
    dut.configure_address<=1
    for i in range(configure_data):
        dut.in_put[i] <= nums[i]
    dut.EN_in_put <= 1
    dut.EN_out_get<=1
    yield RisingEdge(dut.CLK)
    dut.EN_in_put <= 0
    yield RisingEdge(dut.CLK)
    got = int(dut.out_get.value)

    exp = sum(nums) // BUS_WIDTH

    assert got == exp, "Mismatch detected: got {}, expected {}!".format(got, exp)


class ConfigDriver(BusDriver):
    _signals = ['configure_address', 'configure_data',
                'EN_configure', 'RDY_configure']
    async def _monitor_recv(self):
        """Watch the pins and reconstruct transactions."""

        while True:
            await RisingEdge(self.CLK)
            await ReadOnly()
            if self.bus.EN_configure.value:
                self._recv(int(self.bus.configure_data.value))

    def __init__(self, dut, CLK):
        self.CLK = dut.CLK
        self.RST_N = dut.RST_N
        self.in_put = dut.in_put
        self.configure_address  = dut.configure_address
        self.configure_data  = dut.configure_data 
        self.EN_in_put = dut.EN_in_put
        self.EN_out_get = dut.EN_out_get
        self.EN_configure = dut.EN_configure
        self.RST_N<=0
        self.clk<=0
        self.EN_out_get<=0
        BusDriver.__init__(self)
        pass

    @cocotb.coroutine
    def _driver_send(self, txn, sync=True):
        cocotb.fork(Clock(dut.CLK, 10, units='ns').start())
        if sync:
            yield RisingEdge(self.CLK)

        while True:
            yield FallingEdge(self.CLK)

            self.EN_configure <= 1
        pass

class GetMonitor(BusMonitor):

    _signals = ["EN_out_get", "out_get"]

    async def _monitor_recv(self):
        """Watch the pins and reconstruct transactions."""

        while True:
            await RisingEdge(self.CLK)
            await ReadOnly()
            if self.bus.EN_out_get.value:
                self._recv(int(self.bus.out_get.value)
    pass
