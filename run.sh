#/bin/bash

for BW in $(seq 5 10 300)
    do for traffic in LINEAR RANDOM
        do for paging in open close close_adaptive
            do for bank in 8 16
                do
                gem5/build/NULL/gem5.opt --outdir=results_bank/$traffic/LLM_$paging/$bank/BW_$BW -re configs-test-llm/run_llm_eval.py LLM 1 0 60 $paging 256 1 $bank $traffic 1us $BW 100 0
            done
        done
        # gem5/build/NULL/gem5.opt --outdir=results/$traffic/HBM/BW_$BW -re configs-test-llm/run_llm_eval.py HBM 8 0 60 open 1 $traffic 1us $BW 100 0
    done
done