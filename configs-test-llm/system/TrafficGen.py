def createLinearTraffic(tgen, tgen_options):
    yield tgen.createLinear(tgen_options.duration,
                            tgen_options.min_addr,
                            tgen_options.max_addr,
                            tgen_options.block_size,
                            tgen_options.min_period,
                            tgen_options.max_period,
                            tgen_options.rd_perc, 0)
    yield tgen.createExit(0)

def createRandomTraffic(tgen, tgen_options):
    yield tgen.createRandom(tgen_options.duration,
                            tgen_options.min_addr,
                            tgen_options.max_addr,
                            tgen_options.block_size,
                            tgen_options.min_period,
                            tgen_options.max_period,
                            tgen_options.rd_perc, 0)
    yield tgen.createExit(0)

def createStridedTraffic(tgen, tgen_options):
    index = tgen_options.index
    for iteration in range(10):
        address = (iteration * 32 + index) * 64
        print('index: ', index, 'iteration: ', iteration, 'address: ', address)
        yield tgen.createLinear(tgen_options.max_period,
                                address,
                                address + 64,
                                tgen_options.block_size,
                                tgen_options.min_period,
                                tgen_options.max_period,
                                tgen_options.rd_perc, 0)
    yield tgen.createExit(0)