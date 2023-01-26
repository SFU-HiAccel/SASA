KERNEL: DILATE
COUNT: 12
ITERATE: 512
REPEAT: 1
BOARDER: streaming
input s(9720, 1024)
local t1 = if(s(0,2)>s(1,1), s(0,2), s(1,1))
local t2 = if(s(1,2)>s(1,3), s(1,2), s(1,3))
local t3 = if(s(2,0)>s(2,1), s(2,0), s(2,1))
local t4 = if(s(2,2)>s(2,3), s(2,2), s(2,3))
local t5 = if(s(2,4)>s(3,1), s(2,4), s(3,1))
local t6 = if(s(3,2)>s(3,3), s(3,2), s(3,3))
local t7 = if(t1>t2, t1, t2)
local t8 = if(t3>t4, t3, t4)
local t9 = if(t5>t6, t5, t6)
local t10 = if(t7>t8, t7, t8)
local t11 = if(t9>s(4,2), t9, s(4,2))
output y(0, 0) = if(t10>t11, t10, t11)