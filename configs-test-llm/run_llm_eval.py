from m5.util.convert import *
from m5.util import addToPath
# import m5.pystats.loader as loader
addToPath('system')
addToPath('../gem5/configs')

from TestBenchSystem import *
from TrafficGen import *

import argparse
import math


parser = argparse.ArgumentParser()

parser.add_argument('mem_type', type = str,
                    help = '''memory model to simulate''')

parser.add_argument('num_chnls', type = int, default = 1,
                    help = 'number of channels in the memory system, \
                    could only be a power of 2, e.g. 1, 2, 4, 8, ..')

parser.add_argument('banks_per_channel', type = int, default = 32,
                    help = 'number of banks per LLM channel')
                    
parser.add_argument('unified_queue', type = int, default = False,
                    help = 'Unified queue at the MemScheduler')

parser.add_argument('wr_perc', type = int,
                    help = '''Percentage of write request
                    to force servicing writes in MemScheduler''')

parser.add_argument('paging_policy', type = str,
                    help = '''paging policy''')

parser.add_argument('num_tgens', type = int, default = 1,
                    help = 'number of traffic generators to create \
                        synthetic traffic')

parser.add_argument('mode', type = str,
                    help = 'type of traffic to be generated')

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

system = TestBenchSystem(options)
options.block_size = 64
options.duration = int(toLatency(options.duration) * 1e12)
options.min_addr = 0
options.max_addr = toMemorySize(str(512 * options.num_chnls) + 'MB')

injection_period = int((1e12 * options.block_size) /
                    (options.injection_rate * 1073741824))
options.min_period = injection_period
options.max_period = injection_period

root = Root(full_system = False, system = system)


m5.instantiate()

if options.mode == 'LINEAR':
    for i, tgen in enumerate(system.tgens):
        options.min_addr = i * 64
        tgen.start(createLinearTraffic(tgen, options))
# elif options.mode == 'LINEAR':
#     for tgen in system.tgens:
#         tgen.start(createLinearTraffic(tgen, options))
elif options.mode == 'RANDOM':
    for tgen in system.tgens:
        tgen.start(createRandomTraffic(tgen, options))
else:
    print('Traffic type not supported!')

exit_event = m5.simulate()
# simstat = loader.get_simstat(root)
# with open('test.json', 'w') as f:
#     simstat.dump(f)