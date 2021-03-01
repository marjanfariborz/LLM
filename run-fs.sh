#/bin/bash
# rm -r results-gapbs
# for app in pr bfs cc bc tc sssp
for app in bfs cc
    do for size in 20 21 22
        do
        gem5/build/X86/gem5.opt --outdir=/scr/fariborz/results-gapbs/Size_$size/App_$app -re configs/run_gapbs.py vmlinux-5.2.3 /scr/fariborz/gapbs-image/gapbs simple 1 classic $app 1 $size &
    done
done