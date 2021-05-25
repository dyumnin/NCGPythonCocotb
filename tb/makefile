TOPLEVEL_LANG ?= verilog
SIM ?= icarus

PWD=$(shell pwd)


ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(PWD)/../rtl/sumofN.v
else
    $(error "A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif

TOPLEVEL    := sumofN
MODULE      := tb_SumOfN

include $(shell cocotb-config --makefiles)/Makefile.sim