
SHELL=/bin/bash

.PHONY: all clean

all:
TOPLEVEL_LANG ?= verilog
SIM ?= icarus

PWD=$(shell pwd)

ifeq ($(TOPLEVEL_LANG),verilog)
			VERILOG_SOURCES = $(PWD)/../rtl/sumofN.v
else
		$(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif

TOPLEVEL    := sumofN
MODULE      := rtltb

include $(shell cocotb-config --makefiles)/Makefile.sim
clean::
	rm -rf sumofN.vcd sim_build __pycache__ results.xml
