# SASA
SASA is a scalable and automatic stencil acceleration framework on modern HBM-based FPGAs. It automatically generates exploits the best spatial  and temporal parallelism configuration on cloud FPGA platform. If you use SASA in your research, please cite our paper:

> Xingyu Tian, Zhifan Ye, Alec Lu, Licheng Guo, Yuze Chi, and Zhenman Fang. 2022. SASA: A Scalable and Automatic Stencil Acceleration Framework for Optimized Hybrid Spatial and Temporal Parallelism on HBM-based FPGAs.  arXiv:2208.10770
(To be updated)

## Download 

git clone https://github.com/SFU-HiAccel/SASA.git

## Setup Requirement

1. Evaluated hardware platforms:
	+ Host OS
		+ 64-bit Ubuntu 18.04.2 LTS
	+ Datacenter FPGA 
		+ Xilinx Alveo U280 - HBM2-based FPGA
2. Software tools:
	+ HLS tool:
		+ Vitis 2020.1, 2021.1 or 2021.2
		+ Xilinx Runtime (XRT)
	+ Python 3.6+
	+ [TAPA](https://github.com/UCLA-VAST/tapa)
	
## SASA DLS Example
```
# Kernel name
kernel: JACOBI2D

# Required iteration
iteration: 4

# Input name and size
input float: in_1(9720, 1024)
# Stencil kernel pattern with relative coordinates
output float: out_1(0, 0) = ( in_1(0,1) + in_1(1,0) + in_1(0,0) + in_1(0,−1) + in_1(−1,0) ) / 5

# Optional parameters can be decided automatically or user can specify congfiguration
# Kernel number
count: 3
# PE number per kernel
repeat: 4
# Parallelism
boarder: streaming
```

## Usage 

SASA takes high-level description dsl as inputs, automatically explore space oif spatial and temporal parallelism.

1. Generate stencil design with the best optimization: 
	+ Run: `python3 exploration.py --src stencil.dsl `

2. Generate custmized stencil design
	+ Generate the both host code and kenrel code
		+ Run:  `python codgen.py --src stencil.dsl`
	+ Process HLS synthesis
		+ Run: `source generate_xo.sh`
	+ Generate bitstream
		+ Run: `source generate_bitstream.sh
	+ Generate host code
		+ Run: `g++ -o stencil -O2 stencil.cpp host.cpp -ltapa -lfrt -lglog -lgflags -lOpenCL`

3. Execute on hardware
	+ Run: `./stencil --bitstream=stencil.$platform.hw.xclbin`


## Contact
+ [Xingyu Tian](http://www.sfu.ca/~xingyut/), Phd Student 
+ HiAccel Lab, Simon Fraser University (SFU)
+ Supervisor: [Dr. Zhenman Fang](http://www.sfu.ca/~zhenman/group.html)
+ Email: xingyu_tian@sfu.ca
