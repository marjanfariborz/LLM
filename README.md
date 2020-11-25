
## Setup
```
git clone git@github.com:darchr/gem5.git
cd gem5
git checkout LLMScheduler
scons build/NULL/gem5.opt -j $(nproc)
```
## Usage:

```
gem5/build/NULL/gem5.opt  configs-test-llm/run_llm_eval.py (mem_type: LLM, HBM) (num_channels) (num_tgens) (mode: LINEAR, RANDOM) (duration: e.g. 1us, 1ns, ..) (injection_rate in GB/s) (rd_percentage) (data_limit)

```

## TODO:
- [ ] Change queue implementation to class
- [ ] Fix: Arbitration should send packets to the memory controller in each iteration of processNextReqEvent
- [ ] Add stats
    * Head of the queue delay
    * Average queueing delay
- [ ] Add more params to the run and config script (e.g. write max threshold)
- [ ] Packet queue limit beyond 128 (talk to Jason about this)
- [ ] Service read requests to on the fly write requests
- [ ] Associative search on each queue

## TESTS:
* Stress tests:
    MemScheduler: Changing the size of read and write queue to 1 and infinity
    Memory controller: Change the size of read queue to 1
* Compare 2x unfied queue with 1x read and write queue
* Different paging policies
* change the write threshold percentage in MemScheduler

