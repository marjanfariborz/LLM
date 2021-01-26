#/bin/bash
rm -rf results/
for BW in `seq 1 1 20`
    do for traffic in LINEAR RANDOM
        do
        gem5/build/NULL/gem5.opt --outdir=results/LLM_32/$traffic/BW_$BW -re configs-test-llm/run_llm_eval.py LLM 2 32 0 60 close 16 $traffic 10us $BW 100 0 &
        gem5/build/NULL/gem5.opt --outdir=results/LLM_64/$traffic/BW_$BW -re configs-test-llm/run_llm_eval.py LLM 2 64 0 60 close 16 $traffic 10us $BW 100 0 &
        gem5/build/NULL/gem5.opt --outdir=results/HBM/$traffic/BW_$BW -re configs-test-llm/run_llm_eval.py HBM 8 0 0 60 open 16 $traffic 10us $BW 100 0 &
    done
done
