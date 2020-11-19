from m5.util.convert import *
from m5.util import addToPath
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

system = TestBenchSystem(options.mem_type, options.num_chnls, options.num_tgens)

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
    # i = 0
    for tgen in system.tgens:
        # i = i + 1
        # options.min_period = int(options.min_period * math.sqrt(i) / 1.3)
        # options.max_period = int(options.max_period * math.sqrt(i) / 1.3)
        tgen.start(createLinearTraffic(tgen, options))
elif options.mode == 'RANDOM':
    # i = 0
    for tgen in system.tgens:
        # i = i + 1
        # options.min_period = int(options.min_period * math.sqrt(i) / 1.3)
        # options.max_period = int(options.max_period * math.sqrt(i) / 1.3)
        tgen.start(createRandomTraffic(tgen, options))
else:
    print('Traffic type not supported!')

exit_event = m5.simulate()