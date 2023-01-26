from codegen import hls_kernel_gen
from codegen import head_gen
from codegen import buffer
from codegen import host_gen
from codegen import hbm_gen

from core.utils import find_refs_by_offset


def hls_codegen(stencil):
    input_buffer_configs = {}
    for input_var in stencil.input_vars:
        var_references = stencil.all_refs[input_var]
        refs_by_offset = find_refs_by_offset(var_references, stencil.size)
        input_buffer_configs[input_var] = (buffer.InputBufferConfig(input_var, refs_by_offset, 16, stencil.size))

    output_buffer_config = buffer.OutputBufferConfig(stencil.output_var,
                                                     input_buffer_configs[stencil.input_vars[-1]].lineBuffer.min_block_offset,
                                                     input_buffer_configs[stencil.input_vars[-1]].lineBuffer.max_block_offset)

    with open('%s.h' % stencil.app_name, 'w') as file:
        head_gen.head_gen(stencil, file, output_buffer_config)

    with open('host.cpp', 'w') as file:
        host_gen.host_gen(stencil, file, input_buffer_configs, output_buffer_config)

    # with open('hbm_config.h', 'w') as head_file:
    #     with open('settings.cfg', 'w') as cfg_file:
    #         hbm_gen.hbm_files_gen(stencil, head_file, cfg_file)

    # if stencil.iterate == 1 or stencil.boarder_type == 'overlap':
    with open('unikernel.cpp', 'w') as file:
        hls_kernel_gen.kernel_gen(stencil, file, input_buffer_configs, output_buffer_config)