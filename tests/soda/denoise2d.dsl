KERNEL: DENOISE2D
COUNT: 3
ITERATE: 2
BOARDER: streaming
scalar f
input u(9720, 32)

local diff_u_0_1 = u(0, 1) - u( 0,  0)
local diff_d_0_1 = u(0, 1) - u( 0,  2)
local diff_l_0_1 = u(0, 1) - u(-1,  1)
local diff_r_0_1 = u(0, 1) - u( 1,  1)
local g_0_1 = 1/sqrt(1 + diff_u_0_1*diff_u_0_1 + diff_d_0_1*diff_d_0_1 + diff_l_0_1*diff_l_0_1 + diff_r_0_1*diff_r_0_1)

local diff_u_0_m1 = u(0, -1) - u( 0, -2)
local diff_d_0_m1 = u(0, -1) - u( 0,  0)
local diff_l_0_m1 = u(0, -1) - u(-1, -1)
local diff_r_0_m1 = u(0, -1) - u( 1, -1)
local g_0_m1 = 1/sqrt(1 + diff_u_0_m1*diff_u_0_m1 + diff_d_0_m1*diff_d_0_m1 + diff_l_0_m1*diff_l_0_m1 + diff_r_0_m1*diff_r_0_m1)

local diff_u_m1_0 = u(-1, 0) - u(-1, -1)
local diff_d_m1_0 = u(-1, 0) - u(-1,  1)
local diff_l_m1_0 = u(-1, 0) - u(-2,  0)
local diff_r_m1_0 = u(-1, 0) - u( 0,  0)
local g_m1_0 = 1/sqrt(1 + diff_u_m1_0*diff_u_m1_0 + diff_d_m1_0*diff_d_m1_0 + diff_l_m1_0*diff_l_m1_0 + diff_r_m1_0*diff_r_m1_0)

local diff_u_1_0 = u(1, 0) - u(1, -1)
local diff_d_1_0 = u(1, 0) - u(1,  1)
local diff_l_1_0 = u(1, 0) - u(0,  0)
local diff_r_1_0 = u(1, 0) - u(2,  0)
local g_1_0 = 1/sqrt(1 + diff_u_1_0*diff_u_1_0 + diff_d_1_0*diff_d_1_0 + diff_l_1_0*diff_l_1_0 + diff_r_1_0*diff_r_1_0)

local r0 = u(0, 0) * f * 4.9
local r1 = (r0 * (2.5 + r0 * (10.2 + r0))) * (4.3 + r0 * (5.4 + r0 * ( 6.3 + r0)))
output out(0, 0) = (u(0, 0) + 7.7 *
        (u( 0,  1) * g_0_1 +
         u( 0, -1) * g_0_m1 +
         u(-1,  0) * g_m1_0 +
         u( 1,  0) * g_1_0) +
        5.7 * f * r1) * (11.1 + 7.7 *
        (g_0_1 +
         g_0_m1 +
         g_m1_0 +
         g_1_0 + 5.7f))