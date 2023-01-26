KERNEL: JACOBI3D
COUNT: 12
REPEAT: 1
ITERATE: 512
BOARDER: streaming
input t1(9720, 32, 32)
output t0(0, 0, 0) = (t1(0,0,0) + t1(1,0,0) + t1(-1,0,0) + t1(0,1,0) + t1(0,-1,0) + t1(0,0,1) + t1(0,0,-1))*0.142857142