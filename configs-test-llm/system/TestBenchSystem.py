from __future__ import print_function
from __future__ import absolute_import

import m5
from m5.objects import *
from common import ObjectList

import math

class TestBenchSystem(System):

    def __init__(self, options):
        super(TestBenchSystem, self).__init__()
        if options.mem_type == 'LLM':
            self._mem_type = LLM2
            self._addr_mapping = 'RoCoRaBaCh'
            self._paging_policy = options.paging_policy
            self._unified_queue = options.unified_queue
            self._wr_perc = options.wr_perc
            self._bank_per_channel = 32
        elif options.mem_type == 'HBM':
            self._mem_type = HBM_1000_4H_1x128
            self._addr_mapping = HBM_1000_4H_1x128.addr_mapping
            self._paging_policy = HBM_1000_4H_1x128.page_policy
        else:
            fatal('Memory type not supported.')
        self._num_chnls = options.num_chnls
        self._num_tgens = options.num_tgens

        self._mem_size = str(512 * options.num_chnls) + 'MB'
        self._addr_range = AddrRange(self._mem_size)

        self.clk_domain = SrcClockDomain()
        self.clk_domain.clock = '4GHz'
        self.clk_domain.voltage_domain = VoltageDomain()
        self.cache_line_size = 64

        self.mmap_using_noreserve = True
        self.mem_mode = 'timing'
        self.mem_ranges = [self._addr_range]

        self.tgens = [PyTrafficGen() for i in range(self._num_tgens)]
        self.createMemoryCtrl()
        self.connectComponents()
        ####
        # self.membuses = [SystemXBar(width = 64, max_routing_table_size = 16777216) for i in range(self._num_tgens)]
        # self.scheds = [MemScheduler(resp_buffer_size = 64) for i in range(self._num_chnls)]

        # for i, tgen in enumerate(self.tgens):
        #     tgen.port = self.membuses[i].cpu_side_ports

        # for i, membus in enumerate(self.membuses):
        #     for sched in self.scheds:
        #         sched.cpu_side[i] = membus.mem_side_ports

        # for i in range(self._num_chnls):
        #     for j in range(i * 8, (i + 1) * 8):
        #         self.scheds[i].mem_side[j - i * 8] = self.mem_ctrls[j].port

        # self.system_port = self.membuses[0].slave

    def createMemoryCtrl(self):
        mem_ctrls = []
        bpc = 0
        cls = self._mem_type
        addr_range = self._addr_range
        addr_map = self._addr_mapping
        page_policy = self._paging_policy
        if self._mem_type == LLM2:
            bpc = self._bank_per_channel
            num_chnls = self._num_chnls * bpc
        elif self._mem_type == HBM_1000_4H_1x128:
            num_chnls = self._num_chnls
        else:
            fatal('Memory type not supported.')

        intlv_size = self.cache_line_size
        if addr_map == 'RoRaBaChCo':
            rowbuffer_size = cls.device_rowbuffer_size.value * \
                            cls.devices_per_rank.value
            intlv_low_bit = int(math.log(rowbuffer_size, 2))
        else:
            intlv_low_bit = int(math.log(intlv_size, 2))
        intlv_bits = intlv_bits = int(math.log(num_chnls, 2))

        for chnl in range(num_chnls):
            interface = cls()
            interface.range = AddrRange(addr_range.start, size = addr_range.size(),
                        intlvHighBit = intlv_low_bit + intlv_bits - 1,
                        xorHighBit = 0,
                        intlvBits = intlv_bits,
                        intlvMatch = chnl)

            # interface.read_buffer_size = 32
            # interface.write_buffer_size = 16

            ctrl = MemCtrl()
            ctrl.dram = interface

            ctrl.dram.null = True
            ctrl.dram.addr_mapping = addr_map
            ctrl.dram.page_policy = page_policy

            mem_ctrls.append(ctrl)
            if self._mem_type == LLM2:
                ctrl.dram.read_buffer_size = 2
                ctrl.dram.page_policy = page_policy

        self.mem_ctrls = mem_ctrls
    def connectComponents(self):

        if self._mem_type == LLM2:
            self.membuses = [SystemXBar(width = 64, max_routing_table_size = 16777216) for i in range(self._num_tgens)]
            self.scheds = [MemScheduler(read_buffer_size = 1, write_buffer_size = 32, resp_buffer_size = 64, unified_queue = self._unified_queue, \
                            service_write_threshold = self._wr_perc) for i in range(self._num_chnls)]

            bpc = self._bank_per_channel
            for i, tgen in enumerate(self.tgens):
                tgen.port = self.membuses[i].cpu_side_ports

            for i, membus in enumerate(self.membuses):
                for sched in self.scheds:
                    sched.cpu_side[i] = membus.mem_side_ports

            # for i in range(self._num_chnls):
            #     for j in range(i * bpc, (i + 1) * bpc):
            #         self.scheds[i].mem_side[j -  i * bpc] = self.mem_ctrls[j].port
            
            for i, mem_ctrl in enumerate(self.mem_ctrls):
                self.scheds[i % self._num_chnls].mem_side = mem_ctrl.port


            self.system_port = self.membuses[0].cpu_side_ports
        elif self._mem_type == HBM_1000_4H_1x128:
            self.membuses = SystemXBar(width = 64, max_routing_table_size = 16777216)
            for tgen in self.tgens:
                tgen.port = self.membuses.cpu_side_ports
            for mem_ctrl in self.mem_ctrls:
                self.membuses.mem_side_ports = mem_ctrl.port
            self.system_port = self.membuses[0].cpu_side_ports
        else:
            fatal('Memory type not supported.')








