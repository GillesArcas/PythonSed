# must be tested after w1.sed which creates tmp files
# tmp files are reset before reading first input line
1,2r tmp1.txt
3w tmp1.txt
1,2r tmp2.txt
3s/.*/&&/w tmp2.txt
