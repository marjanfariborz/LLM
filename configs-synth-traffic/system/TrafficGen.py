def createLinearTraffic(system, tgen_options):
    yield system.tgen.createLinear(tgen_options.duration, tgen_options.min_addr, tgen_options.max_addr, tgen_options.block_size, tgen_options.min_period, tgen_options.max_period, tgen_options.rd_perc, 0)
    yield system.tgen.createExit(0)

def createRandomTraffic(system, tgen_options):
    yield system.tgen.createRandom(tgen_options.duration, tgen_options.min_addr, tgen_options.max_addr, tgen_options.block_size, tgen_options.min_period, tgen_options.max_period, tgen_options.rd_perc, 0)
    yield system.tgen.createExit(0)

def createDramTraffic(system, tgen_options):
    page_size = system.mem_ctrls[0].devices_per_rank.value * \
                system.mem_ctrls[0].device_rowbuffer_size.value
    max_stride = min(512, page_size)
    addr_map = ObjectList.dram_addr_map_list.get(options.addr_map)
    burst_size = int((system.mem_ctrls[0].devices_per_rank.value *
                  system.mem_ctrls[0].device_bus_width.value *
                  system.mem_ctrls[0].burst_length.value) / 8)

    nbr_banks = system.mem_ctrls[0].banks_per_rank.value
    for stride_size in range(burst_size, max_stride + 1, burst_size):
        for bank in range(1, nbr_banks + 1):
            num_seq_pkts = int(math.ceil(float(stride_size) / burst_size))
            yield system.tgen.createDram(tgen_options.duration,
                            tgen_options.min_addr, tgen_options.max_addr, burst_size,
                            tgen_options.min_period, tgen_options.max_period,
                            tgen_options.rd_perc, tgen_options.data_limit,
                            num_seq_pkts, page_size, nbr_banks, bank,
                            addr_map, 2)
    yield system.tgen.createExit(0)
