import copy
import logging
from itertools import chain
from sqlite3 import InterfaceError

from codegen import codegen_utils
from codegen import hls_kernel_codes
import core
from dsl import ir

_logger = logging.getLogger().getChild(__name__)


def kernel_gen(stencil, output_file, input_buffer_configs, output_buffer_config, position='uni'):
    _logger.info('generate kernel code as %s', output_file.name)
    printer = codegen_utils.Printer(output_file)

    includes = ['<hls_stream.h>', '"math.h"', '"%s.h"' % stencil.app_name, "<tapa.h>" ]
    for include in includes:
        printer.println('#include %s' % include)

    printer.println()
    _print_stencil_kernel(stencil, printer)

    printer.println()
    if stencil.repeat_count == 1:
        _print_backbone_tapa(stencil, printer, input_buffer_configs)
    elif stencil.repeat_count == 2:
        _print_backbone_tapa(stencil, printer, input_buffer_configs, 'start')
        _print_backbone_tapa(stencil, printer, input_buffer_configs, 'end')
        _print_multistage_backbone(stencil, printer)
    else:
        _print_backbone_tapa(stencil, printer, input_buffer_configs, 'start')
        _print_backbone_tapa(stencil, printer, input_buffer_configs, 'mid')
        _print_backbone_tapa(stencil, printer, input_buffer_configs, 'end')
        _print_multistage_backbone(stencil, printer)

    printer.println()
    if stencil.boarder_type == 'overlap':
        _print_load_backbone_tapa(stencil, printer, input_buffer_configs)
    elif stencil.kernel_count == 2:
        _print_load_backbone_tapa(stencil, printer, input_buffer_configs, 'top')
        _print_load_backbone_tapa(stencil, printer, input_buffer_configs, 'bot')
    else:
        _print_load_backbone_tapa(stencil, printer, input_buffer_configs, 'top')
        _print_load_backbone_tapa(stencil, printer, input_buffer_configs, 'center')
        _print_load_backbone_tapa(stencil, printer, input_buffer_configs, 'bot')
    
    if stencil.boarder_type == 'overlap':
      _print_inter_kernel_tapa(stencil, printer)
    elif stencil.kernel_count == 2:
      _print_inter_kernel_tapa(stencil, printer, 'top')
      _print_inter_kernel_tapa(stencil, printer, 'bot')
    else:
      _print_inter_kernel_tapa(stencil, printer, 'top')
      _print_inter_kernel_tapa(stencil, printer, 'center')
      _print_inter_kernel_tapa(stencil, printer, 'bot')

    printer.println()
    if position == 'uni':
        _print_interface_tapa(stencil, printer)

def _print_stencil_kernel(stencil: core.Stencil, printer: codegen_utils.Printer):
    all_refs = stencil.all_refs
    ports = []
    for name, positions in all_refs.items():
        for position in positions:
            ports.append("float %s_%s" % (name, '_'.join(codegen_utils.idx2str(idx) for idx in position)))
    for scalar in stencil.scalar_vars:
        ports.append('float %s' % scalar)

    printer.print_func('static float %s_stencil_kernel' % stencil.app_name, ports)
    printer.do_scope('stencil kernel definition')

    def mutate_name(node: ir.Node, relative_idx: (int,)):
        if isinstance(node, ir.Ref):
            real_idx = codegen_utils.cal_relative(node.idx, relative_idx)
            node.name = node.name + '_' + '_'.join(codegen_utils.idx2str(x) for x in real_idx)
        return node

    output_stmt = stencil.output_stmt.visit(mutate_name, stencil.output_idx)

    local_stmts = []
    for i in range(0, len(stencil.local_stmts)):
        local_stmts.append(stencil.local_stmts[i].visit(mutate_name, (0,)*len(stencil.output_idx)))

    printer.println('/*')
    printer.do_indent()
    printer.println(stencil.output_stmt.expr)
    printer.un_indent()
    printer.println('*/')

    for local_stmt in local_stmts:
        printer.println(local_stmt.let.c_expr)
    printer.println('return ' + output_stmt.expr.c_expr + ';')

    printer.un_scope()

def _print_backbone_tapa(stencil: core.Stencil, printer: codegen_utils.Printer, input_buffer_configs, stage='uni'):
    input_names = stencil.input_vars
    input_def = []
    if stage == 'uni':
        for input_var in stencil.input_vars:
            input_def.append('tapa::istream<INTERFACE_WIDTH>& %s' % input_var) 
        input_def.append('tapa::ostream<INTERFACE_WIDTH>& %s' % stencil.output_var)
    if stage == 'start':
        for input_var in stencil.input_vars:
            input_def.append('tapa::istream<INTERFACE_WIDTH>& %s' % input_var) 
        input_def.append('hls::stream<INTERFACE_WIDTH>& %s' % stencil.output_var)
    if stage == 'mid':
        for input_var in stencil.input_vars:
            input_def.append('hls::stream<INTERFACE_WIDTH>& %s' % input_var) 
        input_def.append('hls::stream<INTERFACE_WIDTH>& %s' % stencil.output_var)
    if stage == 'end':
        for input_var in stencil.input_vars:
            input_def.append('hls::stream<INTERFACE_WIDTH>& %s' % input_var) 
        input_def.append('tapa::ostream<INTERFACE_WIDTH>& %s' % stencil.output_var)

    for scalar in stencil.scalar_vars:
        input_def.append('float %s' % scalar)

    # input_def.append('int useless')
    input_def.append('int iters')
    if stage != 'uni':
        input_def.append('int skip')

    if stage == 'uni': 
        printer.print_func('void %s' % stencil.app_name, input_def)
    else:
        printer.print_func('void %s_%s' % (stencil.app_name, stage), input_def)

    printer.do_scope('stencil kernel definition')
    for buffer_instance in input_buffer_configs.values():
        buffer_instance.print_define_buffer(printer)
        printer.println()

    if stage == 'uni':
    # with printer.for_('int iter_idx = iters', 'iter_idx > 0', 'iter_idx--'):
        printer.println('for(int iter_idx = iters; iter_idx > 0; iter_idx--)')
        printer.do_scope()

    for buffer_instance in input_buffer_configs.values():
        buffer_instance.print_init_buffer_from_stream(printer)   #this
        printer.println()

    if stencil.boarder_type == 'overlap':
        if stage == 'uni':
            append = '(TOP_APPEND+BOTTOM_APPEND)*(iter_idx-1)'
        else:
            append = '(TOP_APPEND+BOTTOM_APPEND)*(iters-1)'
    else:
        if stage == 'uni':
            append = '0'
        else:
            append = '(TOP_APPEND+BOTTOM_APPEND)*(iters-1)'
            
    all_refs = stencil.all_refs
    all_ports = []
    for name, positions in all_refs.items():
        ports = []
        for position in positions:
            ports.append("%s_%s" % (name, '_'.join(codegen_utils.idx2str(idx) for idx in position)))
            all_ports.append("%s_%s" % (name, '_'.join(codegen_utils.idx2str(idx) for idx in position)))
        printer.println('float ' + ', '.join(map(lambda x: x + '[PARA_FACTOR]', ports)) + ';')
        for port in ports:
            printer.println('#pragma HLS array_partition variable=%s complete dim=0'
                            % port)
        printer.println()

    printer.println('MAJOR_LOOP:')
    with printer.for_('int i = 0',
                      'i < GRID_COLS/WIDTH_FACTOR*PART_ROWS + ' + append,
                      'i++'):
        printer.println('#pragma HLS pipeline II=1')
        printer.println()
        printer.println('INTERFACE_WIDTH out_temp;')
        printer.println('COMPUTE_LOOP:')
        with printer.for_('int k = 0', 'k < PARA_FACTOR', 'k++'):
            printer.println('#pragma HLS unroll')

            all_refs = stencil.all_refs
            all_ports = []
            for name, positions in all_refs.items():
                ports = []
                for position in positions:
                    ports.append("%s_%s" % (name, '_'.join(codegen_utils.idx2str(idx) for idx in position)))
                    all_ports.append("%s_%s" % (name, '_'.join(codegen_utils.idx2str(idx) for idx in position)))
                printer.println('float ' + ', '.join(map(lambda x: x + '[PARA_FACTOR]', ports)) + ';')
                for port in ports:
                    printer.println('#pragma HLS array_partition variable=%s complete dim=0'
                                    % port)
                printer.println()

            printer.println()
            printer.println('unsigned int idx_k = k << 5;')
            printer.println()

            for name, positions in all_refs.items():
                buffer_instance = input_buffer_configs[name]
                for position in positions:
                    buffer_instance.print_data_retrieve_with_unroll(printer, position,
                                                                    "%s_%s" % (name, '_'.join(
                                                                        codegen_utils.idx2str(idx) for idx in
                                                                        position)))

            printer.println()
            input_for_kernel = []
            for port in ports:
                input_for_kernel.append(port + '[k]')
            for scalar in stencil.scalar_vars:
                input_for_kernel.append(scalar)
            if stage == 'uni':
                printer.println('float result = %s_stencil_kernel(%s);'
                                % (stencil.app_name, ', '.join(input_for_kernel)))
            else:
                printer.println('float result = skip?%s:%s_stencil_kernel(%s);'
                                % (input_for_kernel[ int(len(input_for_kernel) / 2)], stencil.app_name, ', '.join(input_for_kernel)))
            # printer.println('%s[i + TOP_APPEND + OVERLAP_TOP_OVERHEAD].range(idx_k+31, idx_k) = *((uint32_t *)(&result));'
                            # % stencil.output_var)
            printer.println('out_temp.range(idx_k+31, idx_k) = *((uint32_t *)(&result));')

        printer.println('%s.write(out_temp);' % stencil.output_var )
        printer.println()

        for buffer_instance in input_buffer_configs.values():
            buffer_instance.print_data_movement_from_stream(printer)
        printer.println()

    if stencil.iterate or stencil.repeat_count > 1:
        for buffer_instance in input_buffer_configs.values():
            buffer_instance.print_pop_out(printer)
    
    if stage == 'uni':
        printer.un_scope()
        # printer.println('}')

    printer.println('return;')
    printer.un_scope()
    printer.println()

def _print_multistage_backbone(stencil: core.Stencil, printer: codegen_utils.Printer):
    input_def = []
    for input_var in stencil.input_vars:
        input_def.append('tapa::istream<INTERFACE_WIDTH>& %s' % input_var)

    input_def.append('tapa::ostream<INTERFACE_WIDTH>& %s' % stencil.output_var)
    for scalar in stencil.scalar_vars:
        input_def.append('float %s' % scalar)
    input_def.append('int iters')

    #if stencil.boarder_type == 'overlap':
    printer.print_func('void %s' % stencil.app_name, input_def)
    printer.do_scope('multi-stage backbone definition')
    printer.println('#pragma HLS dataflow')

    mid_instance_count = stencil.repeat_count - 1
    printer.println('hls::stream<INTERFACE_WIDTH> '
                    + ', '.join('temp_out_%d' % i for i in range(mid_instance_count))
                    + ';')

    if stencil.boarder_type == 'overlap':
        with printer.for_('int i = 0', 'i < iters', 'i+=STAGE_COUNT'):
            parameter = codegen_utils.get_parameter_printed(stencil.input_vars, stencil.scalar_vars, 'temp_out_0')
            printer.println('%s_start(%s, iters - i, i >= iters);' % (stencil.app_name, parameter))
            for i in range(1, stencil.repeat_count - 1):
                parameter = codegen_utils.get_parameter_printed(['temp_out_%d' % (i-1),], stencil.scalar_vars, 'temp_out_%d' % i)
                printer.println('%s_mid(%s, iters - i - %d, i + %d > iters);' % (stencil.app_name, parameter, i, i))
            parameter = codegen_utils.get_parameter_printed(['temp_out_%d' % (stencil.repeat_count-2),], stencil.scalar_vars, stencil.output_var)
            printer.println('%s_end(%s, iters - i - %d, i + STAGE_COUNT > iters );' % (stencil.app_name, parameter, stencil.repeat_count - 1))
    else:
        with printer.for_('int i = 0', 'i < iters', 'i+=STAGE_COUNT'):
            parameter = codegen_utils.get_parameter_printed(stencil.input_vars, stencil.scalar_vars, 'temp_out_0')
            printer.println('%s_start(%s, STAGE_COUNT, i >= iters);' % (stencil.app_name, parameter))
            for i in range(1, stencil.repeat_count - 1):
                parameter = codegen_utils.get_parameter_printed(['temp_out_%d' % (i-1),], stencil.scalar_vars, 'temp_out_%d' % i)
                printer.println('%s_mid(%s, STAGE_COUNT - %d, i + %d > iters);' % (stencil.app_name, parameter, i, i))
            parameter = codegen_utils.get_parameter_printed(['temp_out_%d' % (stencil.repeat_count-2),], stencil.scalar_vars, stencil.output_var)
            printer.println('%s_end(%s, STAGE_COUNT - %d, i + STAGE_COUNT > iters );' % (stencil.app_name, parameter, stencil.repeat_count - 1))
      
    printer.println('return;')
    printer.un_scope()
    printer.println()

def _print_load_backbone_tapa(stencil: core.Stencil, printer: codegen_utils.Printer, input_buffer_configs, position = 'uni'):
    input_def = []
    input_num = 0
    for input_var in stencil.input_vars:
        input_def.append('tapa::async_mmap<INTERFACE_WIDTH>& %s' % input_var)
    input_def.append('tapa::async_mmap<INTERFACE_WIDTH>& %s' % stencil.output_var)

    for input_num in range(len(stencil.input_vars)):
        input_def.append('tapa::ostream<INTERFACE_WIDTH>& stream_out_%d' % input_num)
    input_def.append('tapa::istream<INTERFACE_WIDTH>& stream_in')
    input_def.append('uint32_t iters')
    if stencil.boarder_type == 'streaming':
        if position == 'top':
            input_def.append('tapa::ostream<INTERFACE_WIDTH>& bot_out')
            input_def.append('tapa::istream<INTERFACE_WIDTH>& bot_in')
        if position == 'center':
            input_def.append('tapa::istream<INTERFACE_WIDTH>& top_in')
            input_def.append('tapa::ostream<INTERFACE_WIDTH>& top_out')
            input_def.append('tapa::ostream<INTERFACE_WIDTH>& bot_out')
            input_def.append('tapa::istream<INTERFACE_WIDTH>& bot_in')
        if position == 'bot':
            input_def.append('tapa::istream<INTERFACE_WIDTH>& top_in')
            input_def.append('tapa::ostream<INTERFACE_WIDTH>& top_out')

    if stencil.boarder_type == 'streaming':
        printer.print_func('void load_%s' % position, input_def)
    else:
        printer.print_func('void load', input_def)
    
    printer.do_scope('load function of async')

    # Each kenrel output bot first, read in top first.
    if stencil.boarder_type == 'streaming' and stencil.kernel_count != 1:
        if position == 'top':
            printer.println('unsigned int bot_in_bound = GRID_COLS/WIDTH_FACTOR*PART_ROWS + (TOP_APPEND + BOTTOM_APPEND) * STAGE_COUNT;')
            printer.println('unsigned int bot_out_bound = GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT;')
            with printer.for_('int k_wr_req = (%s), k_wr_resp = (%s), k_rd_req = (%s), k_rd_resp = (%s)' 
                         % ('GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT',
                            'GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT', 
                            'GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT - TOP_APPEND * STAGE_COUNT',
                            'GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT - TOP_APPEND * STAGE_COUNT'),
                        'k_rd_resp < bot_out_bound || k_wr_resp < bot_in_bound',''):

                printer.println('if (k_wr_req < bot_in_bound && !product.write_addr.full() && !product.write_data.full() && !bot_in.empty()) {')
                printer.println('\tproduct.write_addr.write(k_wr_req);')
                printer.println('\tproduct.write_data.write(bot_in.read());')
                printer.println('\tk_wr_req++;')
                printer.println('}')
                printer.println('if (!product.write_resp.empty()) {')
                printer.println('\tk_wr_resp += (unsigned int)(product.write_resp.read()) + 1;')
                printer.println('}')

                printer.println('if (k_rd_req < bot_out_bound && source.read_addr.try_write(k_rd_req)){' )
                printer.println('\tk_rd_req++;')
                printer.println('}')
                printer.println('if (!source.read_data.empty() && !bot_out.full()) {')
                printer.println('\tINTERFACE_WIDTH temp = source.read_data.read(nullptr);')
                printer.println('\tbot_out.write(temp);')
                printer.println('\tk_rd_resp++;')
                printer.println('}')
                printer.println()
        if position == 'center':
            printer.println('unsigned int top_in_bound = TOP_APPEND * STAGE_COUNT;')
            printer.println('unsigned int top_out_bound = TOP_APPEND * STAGE_COUNT + BOTTOM_APPEND * STAGE_COUNT;')
            printer.println('unsigned int bot_in_bound = GRID_COLS/WIDTH_FACTOR*PART_ROWS + (TOP_APPEND + BOTTOM_APPEND) * STAGE_COUNT;')
            printer.println('unsigned int bot_out_bound = GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT;')
            with printer.for_('int k_wr_req = 0, k_wr_resp = 0, k_rd_req = (%s), k_rd_resp = (%s)' 
                         % ('GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT - TOP_APPEND * STAGE_COUNT',
                            'GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT - TOP_APPEND * STAGE_COUNT'),
                            'k_rd_resp < bot_out_bound || k_wr_resp < top_in_bound',''):
                printer.println('if (k_wr_req < top_in_bound && !product.write_addr.full() && !product.write_data.full() && !top_in.empty()) {')
                printer.println('\tproduct.write_addr.write(k_wr_req);')
                printer.println('\tproduct.write_data.write(top_in.read());')
                printer.println('\tk_wr_req++;')
                printer.println('}')
                printer.println('if (!product.write_resp.empty()) {')
                printer.println('\tk_wr_resp += (unsigned int)(product.write_resp.read()) + 1;')
                printer.println('}')

                printer.println('if (k_rd_req < bot_out_bound && source.read_addr.try_write(k_rd_req)){' )
                printer.println('\tk_rd_req++;')
                printer.println('}')
                printer.println('if (!source.read_data.empty() && !bot_out.full()) {')
                printer.println('\tINTERFACE_WIDTH temp = source.read_data.read(nullptr);')
                printer.println('\tbot_out.write(temp);')
                printer.println('\tk_rd_resp++;')
                printer.println('}')
                printer.println()
            with printer.for_('int k_wr_req = (%s), k_wr_resp = (%s), k_rd_req = (%s), k_rd_resp = (%s)' 
                         % ('GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT',
                            'GRID_COLS/WIDTH_FACTOR*PART_ROWS + TOP_APPEND * STAGE_COUNT', 
                            'TOP_APPEND * STAGE_COUNT',
                            'TOP_APPEND * STAGE_COUNT'),
                            'k_rd_resp < top_out_bound || k_wr_resp < bot_in_bound',''):
                printer.println('if (k_wr_req < bot_in_bound  && !product.write_addr.full() && !product.write_data.full() && !bot_in.empty()) {')
                printer.println('\tproduct.write_addr.write(k_wr_req);')
                printer.println('\tproduct.write_data.write(bot_in.read());')
                printer.println('\tk_wr_req++;')
                printer.println('}')
                printer.println('if (!product.write_resp.empty()) {')
                printer.println('\tk_wr_resp += (unsigned int)(product.write_resp.read()) + 1;')
                printer.println('}')

                printer.println('if (k_rd_req < top_out_bound && source.read_addr.try_write(k_rd_req)){' )
                printer.println('\tk_rd_req++;')
                printer.println('}')
                printer.println('if (!source.read_data.empty() && !top_out.full()) {')
                printer.println('\tINTERFACE_WIDTH temp = source.read_data.read(nullptr);')
                printer.println('\ttop_out.write(temp);')
                printer.println('\tk_rd_resp++;')
                printer.println('}')
                printer.println()
        if position == 'bot':
            printer.println('unsigned int top_in_bound = TOP_APPEND * STAGE_COUNT;')
            printer.println('unsigned int top_out_bound = TOP_APPEND * STAGE_COUNT + BOTTOM_APPEND * STAGE_COUNT;')
            with printer.for_('int k_wr_req = 0, k_wr_resp = 0, k_rd_req = (%s), k_rd_resp = (%s)' 
                         % ('TOP_APPEND * STAGE_COUNT',
                            'TOP_APPEND * STAGE_COUNT'),
                        'k_rd_resp < top_out_bound || k_wr_resp < top_in_bound',''):
                printer.println('if (k_wr_req < top_in_bound && !product.write_addr.full() && !product.write_data.full() && !top_in.empty()) {')
                printer.println('\tproduct.write_addr.write(k_wr_req);')
                printer.println('\tproduct.write_data.write(top_in.read());')
                printer.println('\tk_wr_req++;')
                printer.println('}')
                printer.println('if (!product.write_resp.empty()) {')
                printer.println('\tk_wr_resp += (unsigned int)(product.write_resp.read()) + 1;')
                printer.println('}')

                printer.println('if (k_rd_req < top_out_bound && source.read_addr.try_write(k_rd_req)){' )
                printer.println('\tk_rd_req++;')
                printer.println('}')
                printer.println('if (!source.read_data.empty() && !top_out.full()) {')
                printer.println('\tINTERFACE_WIDTH temp = source.read_data.read(nullptr);')
                printer.println('\ttop_out.write(temp);')
                printer.println('\tk_rd_resp++;')
                printer.println('}')

    printer.println()
    # Basic part
    if stencil.boarder_type == 'overlap':
      printer.println('unsigned int loop_bound = GRID_COLS/WIDTH_FACTOR*PART_ROWS + (TOP_APPEND+BOTTOM_APPEND)*(iters-1) + TOP_APPEND + BOTTOM_APPEND;') 
    else:
      printer.println('unsigned int loop_bound = GRID_COLS/WIDTH_FACTOR*PART_ROWS + (TOP_APPEND+BOTTOM_APPEND) * STAGE_COUNT;')
    if stencil.repeat_count == 1:
      write_req = 'TOP_APPEND + BOTTOM_APPEND'
      write_resp = 'TOP_APPEND + BOTTOM_APPEND'
    else:
      write_req = '(TOP_APPEND + BOTTOM_APPEND) * STAGE_COUNT'
      write_resp = '(TOP_APPEND + BOTTOM_APPEND) * STAGE_COUNT'
    with printer.for_('int k_wr_req = (%s), k_wr_resp = (%s), k_rd_req = 0, k_rd_resp = 0' 
                         % (write_req, write_resp),
                        # % ('0', '0'),
                        'k_rd_resp < loop_bound || k_wr_resp < loop_bound',''):
      #input
      #updat
      printer.println('if (k_rd_req < loop_bound && source.read_addr.try_write(k_rd_req)){' )
      # printer.println('if (k_rd_req < loop_bound %s){' % map(lambda x: '&& %s.read_addr.try_write(k_rd_req)' % x, stencil.input_vars))
      printer.println('\tk_rd_req++;')
      printer.println('}')
      printer.println('if (k_rd_resp < loop_bound && !source.read_data.empty() && !stream_out_0.full()) {')
      printer.println('\tINTERFACE_WIDTH temp = source.read_data.read(nullptr);')
      printer.println('\tstream_out_0.write(temp);')
      printer.println('\tk_rd_resp++;')
      printer.println('}')
      printer.println()

      #output
      printer.println('if (k_wr_req < loop_bound && !product.write_addr.full() && !product.write_data.full() && !stream_in.empty()) {')
      printer.println('\tproduct.write_addr.write(k_wr_req);')
      printer.println('\tproduct.write_data.write(stream_in.read());')
      printer.println('\tk_wr_req++;')
      printer.println('}')
      printer.println('if (!product.write_resp.empty()) {')
      printer.println('\tk_wr_resp += (unsigned int)(product.write_resp.read()) + 1;')
      printer.println('}')
    
    #Streaming version
    # Need read from top and bot
    # 
    printer.un_scope('load function of async')
    printer.println()

def _print_inter_kernel_tapa(stencil: core.Stencil, printer: codegen_utils.Printer, position = 'uni'):
  input_interfaces = []
  memory_interfaces = []
  output_stream = []
  for var in stencil.input_vars:
    input_interfaces.append(var)
    memory_interfaces.append(var)
    output_stream.append((lambda x:'stream_out_%s' % x) (var))
  memory_interfaces.append(stencil.output_var)
  
  if position == 'top':
      printer.print_func('void inter_kernel_top', chain(map(lambda x:'tapa::async_mmap<INTERFACE_WIDTH>& %s' % x, memory_interfaces)
                                                  , map(lambda x:'tapa::ostream<INTERFACE_WIDTH>& %s' % x, output_stream)
                                                  , ['tapa::istream<INTERFACE_WIDTH>& stream_in', ]
                                                  , map(lambda x: 'float %s' % x, stencil.scalar_vars)
                                                  , ['uint32_t iters']
                                                  , ['tapa::ostream<INTERFACE_WIDTH>& bot_out',
                                                     'tapa::istream<INTERFACE_WIDTH>& bot_in']
                                                ))
  elif position == 'center':
      printer.print_func('void inter_kernel_center', chain(map(lambda x:'tapa::async_mmap<INTERFACE_WIDTH>& %s' % x, memory_interfaces)
                                                  , map(lambda x:'tapa::ostream<INTERFACE_WIDTH>& %s' % x, output_stream)
                                                  , ['tapa::istream<INTERFACE_WIDTH>& stream_in', ]
                                                  , map(lambda x: 'float %s' % x, stencil.scalar_vars)
                                                  , ['uint32_t iters']
                                                  , ['tapa::istream<INTERFACE_WIDTH>& top_in',
                                                     'tapa::ostream<INTERFACE_WIDTH>& top_out',
                                                     'tapa::ostream<INTERFACE_WIDTH>& bot_out',
                                                     'tapa::istream<INTERFACE_WIDTH>& bot_in']
                                                ))
  elif position == 'bot':
      printer.print_func('void inter_kernel_bot', chain(map(lambda x:'tapa::async_mmap<INTERFACE_WIDTH>& %s' % x, memory_interfaces)
                                                  , map(lambda x:'tapa::ostream<INTERFACE_WIDTH>& %s' % x, output_stream)
                                                  , ['tapa::istream<INTERFACE_WIDTH>& stream_in', ]
                                                  , map(lambda x: 'float %s' % x, stencil.scalar_vars)
                                                  , ['uint32_t iters']
                                                  , ['tapa::istream<INTERFACE_WIDTH>& top_in',
                                                     'tapa::ostream<INTERFACE_WIDTH>& top_out',]
                                                ))
  else:
      printer.print_func('void inter_kernel', chain(map(lambda x:'tapa::async_mmap<INTERFACE_WIDTH>& %s' % x, memory_interfaces)
                                                      , map(lambda x:'tapa::ostream<INTERFACE_WIDTH>& %s' % x, output_stream)
                                                      , ['tapa::istream<INTERFACE_WIDTH>& stream_in', ]
                                                      , map(lambda x: 'float %s' % x, stencil.scalar_vars)
                                                      , ['uint32_t iters']
                                                    ))
  printer.do_scope()

  with printer.for_('int i = 0', 'i < iters', 'i+=STAGE_COUNT'):
    printer.println('if (i % STAGE_COUNT == 0) {')
    if position == 'top':
      printer.println('\tload_top(%s, %s, %s, stream_in, iters - i, bot_out, bot_in);' % (', '.join(input_interfaces), stencil.output_var, ', '.join(output_stream)))
    elif position == 'center':
      printer.println('\tload_center(%s, %s, %s, stream_in, iters - i, top_in, top_out, bot_out, bot_in);' % (', '.join(input_interfaces), stencil.output_var, ', '.join(output_stream)))
    elif position == 'bot':
      printer.println('\tload_bot(%s, %s, %s, stream_in, iters - i, top_in, top_out);' % (', '.join(input_interfaces), stencil.output_var, ', '.join(output_stream)))
    else:
      printer.println('\tload(%s, %s, %s, stream_in, iters - i);' % (', '.join(input_interfaces), stencil.output_var, ', '.join(output_stream)))
    printer.println('}')
    printer.println('else {')
    if position == 'top':
      printer.println('\tload_top(%s, %s, %s, stream_in, iters - i, bot_out, bot_in);' % (stencil.output_var, ', '.join(input_interfaces), ', '.join(output_stream)))
    elif position == 'center':
      printer.println('\tload_center(%s, %s, %s, stream_in, iters - i, top_in, top_out, bot_out, bot_in);' % (stencil.output_var, ', '.join(input_interfaces), ', '.join(output_stream)))
    elif position == 'bot':
      printer.println('\tload_bot(%s, %s, %s, stream_in, iters - i, top_in, top_out);' % (stencil.output_var, ', '.join(input_interfaces), ', '.join(output_stream)))
    else:
      printer.println('\tload(%s, %s, %s, stream_in, iters - i);' % (stencil.output_var, ', '.join(input_interfaces), ', '.join(output_stream)))
    printer.println('}')
  printer.un_scope()

def _print_interface_tapa(stencil: core.Stencil, printer: codegen_utils.Printer):
    interfaces = []

    for n in range(stencil.kernel_count):
        for var in stencil.input_vars:
          interfaces.append('%s_%d' % (var, n))
        interfaces.append('%s_%d' % (stencil.output_var, n))
    
    printer.print_func('void unikernel', chain(map(lambda x:'tapa::mmap<INTERFACE_WIDTH> %s' % x, interfaces)
                                                ,['uint32_t iters']))
    printer.do_scope()

    for n in range(stencil.kernel_count):
      printer.println('tapa::stream<INTERFACE_WIDTH, 3> k_wr_%d;' % n)
      printer.println('tapa::stream<INTERFACE_WIDTH, 3> k_rd_%d;' % n)

    if stencil.boarder_type == 'streaming' and stencil.kernel_count > 1:
      for n in range(stencil.kernel_count - 1):
        printer.println('tapa::stream<INTERFACE_WIDTH, 3> down_%d;' % n)
        printer.println('tapa::stream<INTERFACE_WIDTH, 3> up_%d;' % n)

    printer.println('tapa::task()')
    if stencil.boarder_type == 'overlap' or stencil.kernel_count == 1:
      if stencil.kernel_count == 1:
          printer.println('\t.invoke(inter_kernel, %s_0, %s_0, k_wr_0, k_rd_0, iters)' % (('_0,').join(stencil.input_vars)
                                                                                        , stencil.output_var))
          printer.println('\t.invoke(%s, k_wr_0, k_rd_0, iters)' % (stencil.app_name))
      else:
        for n in range(stencil.kernel_count):
          printer.println('\t.invoke(inter_kernel, %s_%d, %s_%d, k_wr_%d, k_rd_%d, iters)' % (('_%d, '%n).join(stencil.input_vars), n
                                                                                        , stencil.output_var, n 
                                                                                        , n, n))
          printer.println('\t.invoke(%s, k_wr_%d, k_rd_%d, iters)' % (stencil.app_name, n, n))
    else:
      for n in range(stencil.kernel_count):
        if n == 0:
          printer.println('\t.invoke(inter_kernel_top, %s_%d, %s_%d, k_wr_%d, k_rd_%d, iters, down_0, up_0)' % (('_%d, '%n).join(stencil.input_vars), n
                                                                                        , stencil.output_var, n 
                                                                                        , n, n)) 
        elif n == stencil.kernel_count - 1:
          printer.println('\t.invoke(inter_kernel_bot, %s_%d, %s_%d, k_wr_%d, k_rd_%d, iters, down_%d, up_%d)' % (('_%d, '%n).join(stencil.input_vars), n
                                                                                        , stencil.output_var, n 
                                                                                        , n, n
                                                                                        , n - 1, n - 1))
        else:
          printer.println('\t.invoke(inter_kernel_center, %s_%d, %s_%d, k_wr_%d, k_rd_%d, iters, down_%d, up_%d, down_%d, up_%d)' % (('_%d, '%n).join(stencil.input_vars), n
                                                                                        , stencil.output_var, n 
                                                                                        , n, n
                                                                                        , n-1, n-1
                                                                                        , n, n))
        printer.println('\t.invoke(%s, k_wr_%d, k_rd_%d, iters)' % (stencil.app_name, n, n))
    printer.println(';')
      
    printer.un_scope()
        
    