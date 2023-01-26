KERNEL: HEAT3D
COUNT: 12
REPEAT: 1
ITERATE: 512
BOARDER: streaming
input in(9720, 32, 32)
local cal1 = (in(1,0,0) - 2*in(0,0,0) + in(-1,0,0))/8
local cal2 = (in(0,1,0) - 2*in(0,0,0) + in(0,-1,0))/8
local cal3 = (in(0,0,1) - 2*in(0,0,0) + in(0,0,-1))/8
output out(0,0,0) = cal1+cal2+cal3+in(0,0,0)