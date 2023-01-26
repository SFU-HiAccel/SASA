KERNEL: BLUR
COUNT: 3
ITERATE: 2
REPEAT: 5
BOARDER: streaming
input in(9720, 1024)
output out(0, 0) = (in(-1,0) + in(-1,1) + in(-1,2) + in(0,0) + in(0,1) + in(0,2) + in(1,0) + in(1,1) + in(1,2))/9