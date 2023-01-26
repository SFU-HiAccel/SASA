KERNEL: THREED
COUNT: 12
ITERATE: 2
BOARDER: streaming
input x(1024, 64, 64)
output y(0, 0, 0) = x(-1, 0, 1) * (x(0, 0, 0) + x(1, 1, -2))
