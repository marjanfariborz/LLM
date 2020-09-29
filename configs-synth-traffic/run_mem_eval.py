from m5.util.convert import *
from m5.util import addToPath
addToPath('system')
addToPath('../gem5/configs')

from CachelessSystem import *
from CachedClassicSystem import *
from CachedRubySystem import *
from GarnetSystem import *
from TrafficGen import *

import argparse

parser = argparse.ArgumentParser()

parser.add_argument('system_type', type = str,
                    help = 'type of system you want to simulate')
# TODO: Add choices
parser.add_argument('mem_type', type = str,
                    help = 'type of memory to use')
                    # choices = all_models)

parser.add_argument('num_chnls', type = int, default = 1,
                    help = 'number of channels in the memory system, \
                    could only be a power of 2, e.g. 1, 2, 4, 8, ..')
# TODO: Add choices
parser.add_argument('mode', type = str,
                    help = 'type of traffic to be generated')
                    # choices = ['LINEAR', 'RANDOM', 'DRAM'])

parser.add_argument('duration', type = str,
                    help = '''real time duration to generate traffic
                    e.g. 1s, 1ms, 1us, 1ns''')

parser.add_argument('injection_rate', type = int,
                    help = '''The amount of traffic generated
                    by the traffic generator in GBps''')

parser.add_argument('rd_perc', type = int,
                    help = '''Percentage of read request,
                    rd_perc = 100 - write requests percentage''')

parser.add_argument('data_limit', type = int, default = 0)

options = parser.parse_args()

if options.system_type == 'cacheless':
    system = CachelessSystem(options.mem_type, options.num_chnls)
    options.block_size = cache_line_size[options.mem_type]
elif options.system_type == 'cached_classic':
    system = CachedClassicSystem(options.mem_type, options.num_chnls)
    options.block_size = 8
elif options.system_type == 'cached_ruby':
    system = CachedRubySystem(options.mem_type, options.num_chnls)
    options.block_size = 8
elif options.system_type == 'garnet':
    system = GarnetSystem(options.mem_type, options.num_chnls)
    options.block_size = 8
else:
    fatal('Type of system not supported')

options.duration = int(toLatency(options.duration) * 1e12)
options.min_addr = 0
options.max_addr = toMemorySize(system.getMemSize(
                    options.mem_type, options.num_chnls))

# TODO:Update addr_map based on memory type
options.addr_map = 'RoRaBaCoCh'

injection_period = int((1e12 * options.block_size) /
                    (options.injection_rate * 1073741824))
options.min_period = injection_period
options.max_period = injection_period

root = Root(full_system = False, system = system)

m5.instantiate()

if options.mode == 'LINEAR':
    system.tgen.start(createLinearTraffic(system, options))
elif options.mode == 'RANDOM':
    system.tgen.start(createRandomTraffic(system, options))
elif options.mode == 'DRAM':
    system.tgen.start(createDramTraffic(system, options))
else:
    print('Traffic type not supported!')

exit_event = m5.simulate()