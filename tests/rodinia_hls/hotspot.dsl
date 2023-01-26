KERNEL: HOTSPOT
COUNT: 3
ITERATE: 64
REPEAT: 3
BOARDER: overlap
input power(9720, 1024)
input temp(9720, 1024)
local tmp = temp(0,0) + temp(0,0)
local tmp0 = temp(-1,0) + temp(1,0) - tmp
local tmp1 = temp(0,-1) + temp(0,1) - tmp
local tmp2 = 80 - temp(0,0)
local power_center1 = tmp0*0.949219 + power(-1,0)
local power_center2 = power_center1 + tmp1*0.010535
local power_center3 = power_center2 + tmp2*0.00000514403
output y(0, 0) = 1.296*power_center3
