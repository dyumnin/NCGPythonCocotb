# This flie contains cocotb testbench for coding test


import math
import os
from random import getrandbits
from typing import Dict, List, Any

import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly, Lock, Timer
from cocotb.queue import Queue
from cocotb.handle import SimHandleBase
from cocotb_bus import monitors
from cocotb_bus.scoreboard import Scoreboard
from cocotb_bus.drivers import BusDriver
from cocotb_bus.drivers import ValidatedBusDriver
from cocotb_bus.monitors import BusMonitor
from cocotb.regression import TestFactory
from cocotb.generators.byte import random_data, get_bytes
from cocotb.generators.bit import (wave, intermittent_single_cycles,
                                   random_50_percent)
import random
import warnings

# Parameters
# N = int(cocotb.top.N)
N = 5


# Main Sum2NTB, instantiates DataDrives and monitors
class Sum2NTB(object):

    # @cocotb.coroutine()
    def __init__(self, dut, debug=False):
        self.dut = dut
        self.stream_in = DataBusDriver(dut, "", dut.CLK)
        self.stream_out = DataBusOut(dut, "", dut.CLK)

        self.pkts_sent=0
        self.pkt_sum=0
        self.expected_output_test = []
        self.expected_output = []
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.stream_out, self.expected_output_test)

        # Moniter input transactions and invoke callback to 'tb_model' every time
        self.stream_in_recovered = DataBusIn(dut, "", dut.CLK, callback=self.tb_model)

    def tb_model(self, transaction):
        self.expected_output.append(transaction)
        self.pkts_sent += 1 # KEEP SAME ORDER
        self.pkt_sum = BinaryValue( sum( [int.from_bytes(self.expected_output[n],"big") for n in range(self.pkts_sent)] ),
                                n_bits=(8 * 4),
                                bigEndian=False )
        self.expected_output_test = [self.pkt_sum]
        
        
    async def reset(self, duration=20):
        pass

# Monitors output transcations
class DataBusOut(BusMonitor):
    _signals = ["EN_out_get", "out_get"]
    _optional_signals = ["ready"]
    
    _default_config = {"firstSymbolInHighOrderBits": True}	
    def __init__(self, entity, name, clock, *, config={}, **kwargs):	
        BusMonitor.__init__(self, entity, name, clock, **kwargs)	
        self.config = self._default_config.copy()	
        for configoption, value in config.items():	
            self.config[configoption] = value	
            self.log.debug("Setting config option %s to %s", configoption, str(value))
            
    async def _monitor_recv(self):	
        """Watch the pins and reconstruct transactions."""	
        # Avoid spurious object creation by recycling	
        clkedge = RisingEdge(self.clock)	
        rdonly = ReadOnly()	
        def valid():	
            if hasattr(self.bus, "ready"):	
                return self.bus.EN_out_get.value and self.bus.ready.value	
            return self.bus.EN_out_get.value	
        # NB could await on valid here more efficiently?	
        while True:	
            await clkedge	
            await rdonly	
            if valid():	
                vec = self.bus.out_get.value	
                vec.big_endian = self.config["firstSymbolInHighOrderBits"]	
                self._recv(vec.buff)	

# Monitors input transcations               	
class DataBusIn(BusMonitor):	
    _signals = ["EN_in_put", "in_put"]	
    _optional_signals = ["ready"]
    
    _default_config = {"firstSymbolInHighOrderBits": True}	
    def __init__(self, entity, name, clock, *, config={}, **kwargs):	
        BusMonitor.__init__(self, entity, name, clock, **kwargs)	
        self.config = self._default_config.copy()	
        for configoption, value in config.items():	
            self.config[configoption] = value	
            self.log.debug("Setting config option %s to %s", configoption, str(value))	
    async def _monitor_recv(self):	
        """Watch the pins and reconstruct transactions."""	
        # Avoid spurious object creation by recycling	
        clkedge = RisingEdge(self.clock)	
        rdonly = ReadOnly()	
        def valid():	
            if hasattr(self.bus, "ready"):	
                return self.bus.EN_in_put.value and self.bus.ready.value	
            return self.bus.EN_in_put.value	
        # NB could await on valid here more efficiently?	
        while True:	
            await clkedge	
            await rdonly	
            if valid():	
                vec = self.bus.in_put.value	
                vec.big_endian = self.config["firstSymbolInHighOrderBits"]	
                self._recv(vec.buff)

# Main driver for input data
class DataBusDriver(ValidatedBusDriver):
    """Streaming bus driver."""
    _signals = ["EN_in_put", "in_put"]
    _optional_signals = ["ready"]
    
    _default_config = {"firstSymbolInHighOrderBits" : True}
    
    def __init__(self, entity, name, clock, *, config={}, **kwargs):
        ValidatedBusDriver.__init__(self, entity, name, clock, **kwargs)
        
        self.config = DataBusDriver._default_config.copy()

        for configoption, value in config.items():
            self.config[configoption] = value
            self.log.debug("Setting config option %s to %s", configoption, str(value))

        word = BinaryValue(n_bits=len(self.bus.in_put), bigEndian=self.config["firstSymbolInHighOrderBits"],
                           value="x" * len(self.bus.in_put))

        self.bus.EN_in_put  <= 0
        self.bus.in_put   <= word
    
    async def _wait_ready(self):
        await ReadOnly()
        while not self.bus.ready.value:
            await RisingEdge(self.clock)
            await ReadOnly()

    async def _driver_send(self, value, sync=True):
        self.log.debug("Sending DataBusDriver transmission: %r", value)

        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)

        word = BinaryValue(n_bits=len(self.bus.in_put), bigEndian=False)

        # Drive some defaults since we don't know what state we're in
        self.bus.EN_in_put <= 0

        if sync:
            await clkedge

        # Insert a gap where valid is low
        if not self.on:
            self.bus.EN_in_put <= 0
            for _ in range(self.off):
                await clkedge

            # Grab the next set of on/off values
            self._next_valids()

        # Consume a valid cycle
        if self.on is not True and self.on:
            self.on -= 1

        self.bus.EN_in_put <= 1

        word.assign(value)
        self.bus.in_put <= word

        # If this is a bus with a ready signal, wait for this word to
        # be acknowledged
        if hasattr(self.bus, "ready"):
            await self._wait_ready()

        await clkedge
        self.bus.EN_in_put <= 0
        word.binstr   = "x" * len(self.bus.in_put)
        self.bus.in_put <= word

        self.log.debug("Successfully sent Avalon transmission: %r", value)


def random_sizes(min_size=1, max_size=63, npackets=N):
    return [random.randint(min_size, max_size) for i in range(N)]

data_in=random_sizes(1, 63, N)


# MAIN module running COCOTB Test
@cocotb.test()
async def rtltb(dut, data_in=data_in):
    """Test for Sum to N RTL"""
    
    # Clock generation      
    cocotb.fork(Clock(dut.CLK, 10, units='ns').start())
    
    # Configuring DUT
    dut.EN_configure <= 0	
    dut.configure_address <= 0	
    dut.configure_data <= 0	
    await RisingEdge(dut.CLK)	
    await FallingEdge(dut.CLK)	
    dut.EN_out_get <= 0	
    	
    dut.EN_configure <= 1	
    dut.configure_address <= 0	
    dut.configure_data <= N	
    await RisingEdge(dut.CLK)	
    	
    dut.EN_configure <= 1	
    dut.configure_address <= 1	
    dut.configure_data <= 1	
    await RisingEdge(dut.CLK)	
    dut.EN_configure <= 0
    
    tb = Sum2NTB(dut)
    await tb.reset()
    dut.RDY_out_get <= 1

    # Sending and Monitoring Input Data
    await  RisingEdge(dut.CLK)
    for transaction in data_in:
        await tb.stream_in.send(transaction)

    # Wait for 2 cycles after out_en in low
    for i in range(2):
        await RisingEdge(dut.CLK)
        while not dut.RDY_out_get.value:
            await  RisingEdge(dut.CLK)
            
    dut._log.info(f"Input Data into the stream {data_in} flitts")
    
    if N != tb.pkts_sent:
        dut._log.info("DUT recorded %d packets but tb counted %d" % (
                        N, tb.pkts_sent))
    else:
        dut._log.info("DUT correctly counted %d packets" % N)
    
    dut._log.info(f"DUT produces sum = {tb.expected_output_test[0]} ")
    
    rslt_en = dut.RDY_out_get.value
    rslt_val = dut.out_get.value
    
    dut._log.info(f"Values From RTL are Enable: {rslt_en}, Data is: {rslt_val}")
    
    
    # Checking assertion
    assert rslt_val == tb.expected_output_test[0], f"Incorrect, Enable is: {rslt_en}, Data is: {rslt_val}"
    
    assert N == tb.pkts_sent, f"Incorrect, DUT recorded {N} packets but tb counted {tb.pkts_sent}"
    
    
    raise tb.scoreboard.result




