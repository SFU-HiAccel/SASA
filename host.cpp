#include <iostream>
#include <vector>
#include <fstream>
#include "math.h"
#include "BLUR.h"
#include <gflags/gflags.h>
#include <tapa.h>

using std::clog;
using std::endl;
using std::vector;

void unikernel(tapa::mmap<INTERFACE_WIDTH> source_0, 
  tapa::mmap<INTERFACE_WIDTH> product_0, uint32_t iters)
;

DEFINE_string(bitstream, "", "path to bitstream file, run csim if empty");
int main(int argc, char** argv) {
  std::cout << "Program start" << std::endl;

  gflags::ParseCommandLineFlags(&argc, &argv, /*remove_flags=*/true);

  printf("midle_region = %d\n", MIDDLE_REGION);
  vector<INTERFACE_WIDTH>source_0(MIDDLE_REGION);
  vector<INTERFACE_WIDTH>product_0(MIDDLE_REGION);

  const uint32_t iter = ITERATION;

  std::cout << "kernel start" << endl;
  int64_t kernel_time_ns = tapa::invoke(unikernel, FLAGS_bitstream, 
  	tapa::read_write_mmap<INTERFACE_WIDTH> (source_0),
  	tapa::read_write_mmap<INTERFACE_WIDTH> (product_0),
  	iter);
  clog << "kernel time: " << kernel_time_ns * 1e-9 << " s" << endl;

  return 0;
}
