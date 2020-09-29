from __future__ import print_function
from __future__ import absolute_import

import m5
from m5.objects import *
from common import ObjectList

import math

from MI_Example_TrafficGen import *
from info import *
from ds3ini import *

class CachedRubySystem(System):
    def __init__(self, mem_type, num_chnls):
        super(CachedRubySystem, self).__init__()
        mem_size = self.getMemSize(mem_type, num_chnls)
        addr_range = AddrRange(mem_size)

        self.clk_domain = SrcClockDomain()
        self.clk_domain.clock = '4GHz'
        self.clk_domain.voltage_domain = VoltageDomain()
        self.cache_line_size = self.getCachelineSize(mem_type)

        self.mmap_using_noreserve = True
        self.membus = SystemXBar(width = 64)
        self.membus.max_routing_table_size = 16777216
        self.mem_mode = 'timing'
        self.mem_ranges = [addr_range]

        addr_map = 'RoRaBaCoCh'

        self.createMemoryCtrl(mem_type, num_chnls,
                            addr_range, addr_map)

        for mem_ctrl in self.mem_ctrls:
            mem_ctrl.port = self.membus.master

        self.tgen = PyTrafficGen()
        self.tgen.elastic_req = False
        self.monitor = CommMonitor()
        # self.l1cache = L1Cache()
        # self.l1cache.assoc = 4
        # self.l1cache.size = '4MB'
        # self.l1cache.connectCPU(self.tgen)
        # self.l1cache.connectBus(self.monitor)
        self.cache = MIExampleSystem()
        self.cache.setup(self, self.tgen, self.monitor, 'simple')

        self.monitor.master = self.membus.slave
        self.system_port = self.membus.slave

    def getCachelineSize(self, mem_type):
        return cache_line_size[mem_type]

    def getMemSize(self, mem_type, num_chnls):
        return (str(capacity_per_channel[mem_type] * num_chnls) + 'MB')

    def createMemoryCtrl(self, mem_type, num_chnls,
                        addr_range, addr_map):
        mem_ctrls = []

        if mem_type in internal_models:
            cls = ObjectList.mem_list.get(mem_type)
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
                ctrl = MemCtrl()
                # ctrl.write_buffer_size = interface.write_buffer_size
                # ctrl.read_buffer_size = interface.read_buffer_size
                ctrl.dram = interface

                if mem_type in internal_models:
                    ctrl.dram.null = True
                    ctrl.dram.addr_mapping = addr_map

                mem_ctrls.append(ctrl)

        # TODO: Fix multi-channel for DS2 models.
        elif mem_type in dramsim2_models:
            class DS2MemCtrl(DRAMSim2):
                def __init__(self):
                    super(DS2MemCtrl, self).__init__()
                    self.deviceConfigFile = "ini/" + mem_type + ".ini"
            ctrl = DS2MemCtrl()

            mem_ctrls.append(ctrl)

        elif mem_type in dramsim3_models:
            ini_path = init_ds3(mem_type, num_chnls)
            class DS3MemCtrl(DRAMsim3):
                def __init__(self):
                    super(DS3MemCtrl, self).__init__()
                    self.configFile = ini_path
            ctrl = DS3MemCtrl()

            mem_ctrls.append(ctrl)

        # elif mem_options.mem_type in simple_memory:
        #     lat, bw = get_simple_mem_param()
        #     class SMemCtrl(SimpleMemory):
        #         def __init__(self):
        #             super(SMemCtrl, self).__init__()
        #             self.latency = '100ns'
        #             self.bandwidth = '40GB/s'
        #     cls = SMemCtrl

        else:
            print('Memory type not supported')

        self.mem_ctrls = mem_ctrls








