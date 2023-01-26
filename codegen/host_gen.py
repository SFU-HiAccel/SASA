import logging
import copy

from codegen import codegen_utils
from codegen import host_codes

import core
from dsl import ir

_logger = logging.getLogger().getChild(__name__)

def host_gen(stencil, output_file, input_buffer_configs, output_buffer_config):
    _logger.info('generate host code as %s', output_file.name)
    printer = codegen_utils.Printer(output_file)

    # include_files = ['<iostream>', '<string>', '<unistd.h>', '<vector>', '<fstream>', '<sys/time.h>',
    #                  '"math.h"', '"%s.h"' % stencil.app_name,
    #                  '<gflags/gflags.h>', '<tapa.h>']
    include_files = ['<iostream>', '<vector>', '<fstream>',
                      '"math.h"', '"%s.h"' % stencil.app_name,
                      '<gflags/gflags.h>', '<tapa.h>']
    for file_name in include_files:
        printer.println('#include %s' %file_name)
    printer.println()

    printer.println('using std::clog;')
    printer.println('using std::endl;')
    printer.println('using std::vector;')
    printer.println()

    _print_def(stencil, printer, input_buffer_configs, output_buffer_config)

    printer.println('DEFINE_string(bitstream, "", "path to bitstream file, run csim if empty");')
    # printer.println(host_codes.includes)

    # printer.println(host_codes.HBM_def)

    # printer.println(host_codes.reset_function)

    # for buffer in input_buffer_configs.values():
    #     buffer.print_c_load_func(printer)

    # printer.println(host_codes.verify_function)

    _print_main(stencil, printer, input_buffer_configs, output_buffer_config)

def _print_def(stencil, printer, input_buffer_configs, output_buffer_config):
  input_def = []
  for n in range(stencil.kernel_count):
    for input_var in stencil.input_vars:
      input_def.append('tapa::mmap<INTERFACE_WIDTH> %s_%d' % (input_var, n)) 
    input_def.append('tapa::mmap<INTERFACE_WIDTH> %s_%d' % (stencil.output_var, n))
  input_def.append('uint32_t iters')

  printer.print_func('void unikernel', input_def)
  printer.println(';')
  printer.println()

def _print_main(stencil, printer, input_buffer_configs, output_buffer_config):
    # printer.println('////////MAIN FUNCTION//////////')
    printer.println('int main(int argc, char** argv) {')
    printer.do_indent()

    printer.println('std::cout << "Program start" << std::endl;')
    printer.println()

    printer.println('gflags::ParseCommandLineFlags(&argc, &argv, /*remove_flags=*/true);')
    printer.println()

    #Initial buffer
    printer.println('printf("midle_region = %d\\n", MIDDLE_REGION);')
    for n in range(stencil.kernel_count):
      for input_var in stencil.input_vars:
        printer.println('vector<INTERFACE_WIDTH>%s_%d(MIDDLE_REGION);' % (input_var, n))
      printer.println('vector<INTERFACE_WIDTH>%s_%d(MIDDLE_REGION);' % (stencil.output_var, n))
    printer.println()
    
    # Refernce input and output

    # Kernel processing
    printer.println('const uint32_t iter = ITERATION;')
    printer.println()

    printer.println('std::cout << "kernel start" << endl;')
    printer.println('int64_t kernel_time_ns = tapa::invoke(unikernel, FLAGS_bitstream, ')
    for n in range(stencil.kernel_count):
      for input_var in stencil.input_vars:
        printer.println('\ttapa::read_write_mmap<INTERFACE_WIDTH> (%s_%d),' % (input_var, n))
      printer.println('\ttapa::read_write_mmap<INTERFACE_WIDTH> (%s_%d),' % (stencil.output_var, n))
    printer.println('\titer);')

    printer.println('clog << "kernel time: " << kernel_time_ns * 1e-9 << " s" << endl;')
    printer.println()
    # Verification part

    printer.println('return 0;')
    printer.un_indent()
    printer.println('}')

    # if stencil.boarder_type != 'streaming':
    #     printer.println(host_codes.unikernel_init_opencl)
    # else:
    #     printer.println(host_codes.streaming_kernel_init_opencl)
    # printer.println('std::cout << "%s kernel loaded." << std::endl;' % stencil.app_name)

    # printer.println()

    # printer.println('// Init buffers')
    # for buffer in input_buffer_configs.values():
    #     buffer.print_c_buffer_def(printer)
    #     buffer.print_c_buffer_init(printer)
    #     printer.println()

    # output_buffer_config.print_c_buffer_def(printer)

    # printer.println('std::cout << "%s buffers inited." << std::endl;' % stencil.app_name)

    # printer.println()

    # printer.println('// Allocate buffers in global memory')
    # for buffer in input_buffer_configs.values():
    #     buffer.print_c_buffer_allocate(printer)
    #     printer.println()
    # output_buffer_config.print_c_buffer_allocate(printer)
    # printer.println('std::cout << "%s buffers allocated." << std::endl;' % stencil.app_name)

    # printer.println()

    # printer.println('// Set kernel arguments')

    # scalar_list = copy.copy(stencil.scalar_vars)
    # var_list = copy.copy(stencil.input_vars)
    # var_list.append(stencil.output_var)
    # with printer.for_('int i = 0', 'i < KERNEL_COUNT', 'i++'):
    #     count = 0
    #     for var in var_list:
    #         printer.println('OCL_CHECK(err, err = kernels[i].setArg(%d, device_%ss[i]));' % (count, var))
    #         count += 1
    #     for scalar in scalar_list:
    #         printer.println('OCL_CHECK(err, err = kernels[i].setArg(%d, 1.5));' % count)
    #         count += 1

    #     # TODO: CHANGE ITERS VALUE
    #     printer.println('OCL_CHECK(err, err = kernels[i].setArg(%d, 16));' % count)

    #     printer.println()

    #     for var in stencil.input_vars:
    #         printer.println('OCL_CHECK(err, err = q.enqueueMigrateMemObjects({device_%ss[i]}, 0/*means from host*/));'
    #                         % var)

    # printer.println('q.finish();')

    # printer.println('std::cout << "Write device buffer finished" << std::endl;')

    # printer.println()

    # printer.println('struct timeval tv1, tv2;')
    # printer.println('gettimeofday(&tv1, NULL);')

    # printer.println('// Launch kernels')
    # with printer.for_('int i = 0', 'i < KERNEL_COUNT', 'i++'):
    #     printer.println('OCL_CHECK(err, err = q.enqueueTask(kernels[i]));')

    # printer.println('q.finish();')
    # printer.println('std::cout << "Execution finished" << std::endl;')

    # printer.println()

    # printer.println('gettimeofday(&tv2, NULL);')

    # printer.println('std::cout << "Execution finished, kernel execution time cost:" <<')
    # printer.println('\t(tv2.tv_sec-tv1.tv_sec)*1000000 + (tv2.tv_usec - tv1.tv_usec) << "us" << std::endl;')

    # printer.println()

    # printer.println('// Check results')

    # if stencil.iterate%2 == 0:
    #     final_result_buffer = stencil.input_vars[-1]
    # else:
    #     final_result_buffer = stencil.output_var

    # with printer.for_('int i = 0', 'i < KERNEL_COUNT', 'i++'):
    #     printer.println('OCL_CHECK(err, err = q.enqueueMigrateMemObjects({device_%ss[i]}, CL_MIGRATE_MEM_OBJECT_HOST));'
    #                     % final_result_buffer)

    # printer.println('q.finish();')
    # printer.println('std::cout << "Read results finished." << std::endl;')

    # printer.println()

    # printer.println('bool match = verify(%ss);' % final_result_buffer)

    # printer.println('return (match ? EXIT_SUCCESS : EXIT_FAILURE);')

    # printer.un_indent()
    # printer.println('}')