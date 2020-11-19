
## Setup
```
git clone git@github.com:darchr/gem5.git
cd gem5
git checkout LLMScheduler
scons build/NULL/gem5.opt -j $(nproc)
```
## usage:

```
gem5/build/NULL/gem5.opt  configs-test-llm/run_llm_eval.py (mem_type: LLM, HBM) (num_channels) (num_tgens) (mode: LINEAR, RANDOM) (duration: e.g. 1us, 1ns, ..) (injection_rate in GB/s) (rd_percentage) (data_limit)

```