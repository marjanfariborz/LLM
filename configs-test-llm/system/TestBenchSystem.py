from __future__ import print_function
from __future__ import absolute_import

import m5
from m5.objects import *
from common import ObjectList

import math

class TestBenchSystem(System):

    def __init__(self, num_chnls, num_tgens):
        super(TestBenchSystem, self).__init__()
        self._num_chnls = num_chnls
        self._num_tgens = num_tgens

        self._mem_size = str(512 * num_chnls) + 'MB'
        self._addr_range = AddrRange(self._mem_size)

        self.clk_domain = SrcClockDomain()
        self.clk_domain.clock = '4GHz'
        self.clk_domain.voltage_domain = VoltageDomain()
        self.cache_line_size = 64

        self.mmap_using_noreserve = True
        self.mem_mode = 'timing'
        self.mem_ranges = [self._addr_range]

        self.createMemoryCtrl()
        self.tgens = [PyTrafficGen() for i in range(self._num_tgens)]
        self.membuses = [SystemXBar(width = 64, max_routing_table_size = 16777216) for i in range(self._num_tgens)]
        self.scheds = [MemScheduler(nbr_cpus = self._num_tgens, nbr_channels = 8, resp_buffer_size = 64) for i in range(self._num_chnls)]

        for i, tgen in enumerate(self.tgens):
            tgen.port = self.membuses[i].cpu_side_ports

        for i, membus in enumerate(self.membuses):
            for sched in self.scheds:
                sched.cpu_side[i] = membus.mem_side_ports

        for i in range(self._num_chnls):
            for j in range(i * 8, (i + 1) * 8):
                self.scheds[i].mem_side[j - i * 8] = self.mem_ctrls[j].port

        self.system_port = self.membuses[0].slave

    def createMemoryCtrl(self):
        mem_ctrls = []

        addr_range = self._addr_range
        addr_map = LLM2.addr_mapping
        num_chnls = self._num_chnls * 8
        intlv_size = self.cache_line_size

        if addr_map == 'RoRaBaChCo':
            rowbuffer_size = cls.device_rowbuffer_size.value * \
                            cls.devices_per_rank.value
            intlv_low_bit = int(math.log(rowbuffer_size, 2))
        else:
            intlv_low_bit = int(math.log(intlv_size, 2))
        intlv_bits = intlv_bits = int(math.log(num_chnls, 2))

        for chnl in range(num_chnls):
            interface = LLM2()
            interface.range = AddrRange(addr_range.start, size = addr_range.size(),
                        intlvHighBit = intlv_low_bit + intlv_bits - 1,
                        xorHighBit = 0,
                        intlvBits = intlv_bits,
                        intlvMatch = chnl)

            ctrl = MemCtrl()
            ctrl.dram = interface

            ctrl.dram.null = True
            ctrl.dram.addr_mapping = addr_map

            mem_ctrls.append(ctrl)

        self.mem_ctrls = mem_ctrls








