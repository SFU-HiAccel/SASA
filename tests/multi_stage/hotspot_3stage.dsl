KERNEL: MGVF
COUNT: 3
ITERATE: 3
REPEAT: 1
BOARDER: streaming
input I(9720, 1024)
input imgvf(9720, 1024)

local UL = imgvf(-1,-1) - imgvf(0,0)
local U = imgvf(-1,0) - imgvf(0,0)
local UR = imgvf(-1,1) - imgvf(0,0)
local L = imgvf(0,-1) - imgvf(0,0)
local R = imgvf(0,1) - imgvf(0,0)
local DL = imgvf(1,-1) - imgvf(0,0)
local D = imgvf(1,0) - imgvf(0,0)
local DR = imgvf(1,1) - imgvf(0,0)

local HUL = if(UL>0.0001, 0.1*UL, if(UL>-0.0001, 0.05*UL, 0))
local HU = if(U>0.0001, 0.1*U, if(U>-0.0001, 0.05*U, 0))
local HUR = if(UR>0.0001, 0.1*UR, if(UR>-0.0001, 0.05*UR, 0))
local HL = if(L>0.0001, 0.1*L, if(L>-0.0001, 0.05*L, 0))
local HR = if(R>0.0001, 0.1*R, if(R>-0.0001, 0.05*R, 0))
local HDL = if(DL>0.0001, 0.1*DL, if(DL>-0.0001, 0.05*DL, 0))
local HD = if(D>0.0001, 0.1*D, if(D>-0.0001, 0.05*D, 0))
local HDR = if(DR>0.0001, 0.1*DR, if(DR>-0.0001, 0.05*DR, 0))

local t1 = HUL + HU
local t2 = HUR + HL
local t3 = HR + HDL
local t4 = HD + HDR
local t5 = t1 + t2
local t6 = t3 + t4
local t7 = t5 + t6
local vHe = imgvf(0,0) + t7

local diff = vHe - I(0,0)

output y(0, 0) = vHe - 0.2*I(0,0)*diff