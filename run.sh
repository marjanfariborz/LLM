#/bin/bash

for BW in $(seq 5 10 300)
    do for paging in open close close_adaptive
        do
        gem5/build/NULL/gem5.opt --outdir=results2/LINEAR/LLM_$paging/BW_$BW -re configs-test-llm/run_llm_eval.py LLM 1 0 60 $paging 1 LINEAR 1us $BW 100 0
    done
    gem5/build/NULL/gem5.opt --outdir=results2/LINEAR/HBM/BW_$BW -re configs-test-llm/run_llm_eval.py HBM 1 0 60 open 1 LINEAR 1us $BW 100 0
done
