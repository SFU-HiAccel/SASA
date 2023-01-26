import math
import copy
from functools import reduce
import logging

from codegen.codegen_utils import Printer, idx2str, cvt_idx2offset
from codegen import codegen_utils

_logger = logging.getLogger().getChild(__name__)

class Block:
    def __init__(self, var_name, ref_by_offset, size, unroll_factor):
        self.index = ref_by_offset
        self.name = '%s_block_%s' % (var_name, idx2str(ref_by_offset))

class StreamBuffer:
    def __init__(self, var_name, ref_by_offset1, ref_by_offset2, size, unroll_factor):
        self.index = ref_by_offset1
        self.index2 = ref_by_offset2
        self.length = self.index2 - self.index + 1
        self.name = '%s_stream_%s_to_%s' % (var_name, idx2str(ref_by_offset1), idx2str(ref_by_offset2))

class LineBuffer:
    def __init__(self, var_name, refs_by_offset, unroll_factor, size):
        self.unroll_factor = unroll_factor
        self.min_offset = min(refs_by_offset)
        self.max_offset = max(refs_by_offset) + 15
        '''
        if self.min_offset >= 0:
            self.min_row = 0
        else:
            self.min_row = abs(math.floor(self.min_offset / reduce(lambda x,y:x*y, size[1:])))
        if self.max_offset < reduce(lambda x,y:x*y, size[1:]):
            self.max_row = 0
        else:
            self.max_row = abs(math.ceil(self.max_offset / reduce(lambda x,y:x*y, size[1:]))) - 1
        '''

        #TODO: Assume min_offset <= 0 here
        self.min_block_offset = math.ceil(-self.min_offset/self.unroll_factor)
        self.max_block_offset = math.ceil((self.max_offset + 1) / self.unroll_factor)

        self.blocks = list()
        for ref in refs_by_offset:
            if ref % unroll_factor == 0:
                to_add = int(ref / unroll_factor)
                if to_add not in map(lambda block: block.index, self.blocks):
                    self.blocks.append(Block(var_name, to_add, size, unroll_factor))
            else:
                to_add1 = math.floor(ref / unroll_factor)
                to_add2 = to_add1 + 1
                if to_add1 not in map(lambda block: block.index, self.blocks):
                    self.blocks.append(Block(var_name, to_add1, size, unroll_factor))
                if to_add2 not in map(lambda block: block.index, self.blocks):
                    self.blocks.append(Block(var_name, to_add2, size, unroll_factor))

        self.streams = list()
        more_blocks = list()
        for block1, block2 in zip(self.blocks, self.blocks[1:]):
            if block2.index - block1.index == 1:
                pass
            elif block2.index - block1.index == 2:
                more_blocks.append(Block(var_name, block1.index+1, size, unroll_factor))
            else:
                self.streams.append(StreamBuffer(var_name, block1.index+1, block2.index-1, size, unroll_factor))

        for block in more_blocks:
            self.blocks.append(block)

        self.buffer_flow = copy.copy(self.blocks+self.streams)
        self.buffer_flow.sort(key=lambda x: x.index)

    def find_block(self, offset: int) -> Block:
        block_offset = math.floor(offset/self.unroll_factor)
        for block in self.blocks:
            if block_offset == block.index:
                return block
        _logger.error('Block Not Found Error')
        exit(-2)


class InputBufferConfig:

    def __init__(self, var_name, refs_by_offset, unroll_factor, size):
        self.var_name = var_name
        self.refs_by_offset = refs_by_offset
        self.unroll_factor = unroll_factor
        self.size = size
        self.lineBuffer = LineBuffer(var_name, refs_by_offset, unroll_factor, size)


    def print_define_buffer(self, printer: Printer):
        '''Print All Buffer Element Definition'''

        for buffer_element in self.lineBuffer.buffer_flow:
            if type(buffer_element) == Block:
                printer.println('INTERFACE_WIDTH %s;' % buffer_element.name)
            else:
                printer.println('hls::stream<INTERFACE_WIDTH, %s> %s;'
                                % (buffer_element.index2 - buffer_element.index + 2, buffer_element.name))

    def print_init_buffer(self, printer: Printer):
        '''Print HLS code to fill in buffer elements'''
  
        for buffer_element in self.lineBuffer.buffer_flow:
            if type(buffer_element) == Block:
                printer.println('%s = %s[%s + %s];' %
                                (buffer_element.name, self.var_name, self.lineBuffer.min_block_offset, buffer_element.index))
            else:
                with printer.for_('int i = %s + %s'
                                    % (self.lineBuffer.min_block_offset, buffer_element.index),
                                  'i < %s + %s'
                                    % (self.lineBuffer.min_block_offset, buffer_element.index2 + 1),
                                  'i++'):
                    printer.println('%s << %s[i];' % (buffer_element.name, self.var_name))
    
    # def print_init_buffer_streaming(self, printer: Printer):
    #   '''Print HLS code to fill in buffer elements from other kernels'''
    #   for buffer_element in self.lineBuffer.buffer_flow:
    #     if type(buffer_element) == Block:
    #       if buffer_element.index < 0:
    #         printer.println('%s = top_in.read();' %
    #                             (buffer_element.name, self.var_name))
    #       else:
    #         printer.println('%s = %s.read();' %
    #                             (buffer_element.name, self.var_name))
    #     else:
    #       with printer.for_('int i = %s + %s'
    #                                 % (self.lineBuffer.min_block_offset, buffer_element.index),
    #                               'i < %s + %s'
    #                                 % (self.lineBuffer.min_block_offset, buffer_element.index2 + 1),
    #                               'i++'):
    #         if buffer_element.index2 < 0:
    #           printer.println('%s << top_in.read();' % (buffer_element.name))
    #         else:
    #           printer.println('%s << %s.read();' % (buffer_element.name, self.var_name))

    def print_init_buffer_from_stream(self, printer: Printer):
        '''Print HLS code to fill in buffer elements'''

        for buffer_element in self.lineBuffer.buffer_flow:
            if type(buffer_element) == Block:
                printer.println('%s = %s.read();' %
                                (buffer_element.name, self.var_name))
            else:
                with printer.for_('int i = %s + %s'
                                    % (self.lineBuffer.min_block_offset, buffer_element.index),
                                  'i < %s + %s'
                                    % (self.lineBuffer.min_block_offset, buffer_element.index2 + 1),
                                  'i++'):
                    printer.println('%s << %s.read();' % (buffer_element.name, self.var_name))

    def print_data_retrieve_with_unroll(self, printer: Printer, src_idx, dst='', default_stmt='', default_value=0):
        if src_idx[-1] % self.unroll_factor == 0:
            src_offset = cvt_idx2offset(src_idx, self.size)
            printer.println('uint32_t temp_%s = %s.range(idx_k+31, idx_k);'
                            % (dst, self.lineBuffer.find_block(src_offset).name))
            if default_stmt is not '':
                printer.println('%s[k] = (%s)? %s: *((float*)(&temp_%s));'
                            % (dst, default_stmt, str(default_value), dst))
            else:
                printer.println('%s[k] = *((float*)(&temp_%s));'
                                % (dst, dst))
        else:
            src_offset1 = cvt_idx2offset(src_idx, self.size)
            src_offset2 = src_offset1 + self.unroll_factor
            block1 = self.lineBuffer.find_block(src_offset1)
            block2 = self.lineBuffer.find_block(src_offset2)

            block1_align_left = (src_offset1 - block1.index*self.unroll_factor)*32
            block1_align_right = block1_align_left + 31
            block2_align_left = (src_offset1 - block2.index*self.unroll_factor)*32
            block2_align_right = block2_align_left + 31
            k_to_switch = int(abs(block2_align_left/32))
            printer.println('uint32_t temp_%s = (k<%s)?%s.range(idx_k + %s, idx_k + %s)'
                            ' : %s.range(idx_k + %s, idx_k + %s);'
                            % (dst, str(k_to_switch), block1.name, block1_align_right, block1_align_left,
                               block2.name, block2_align_right, block2_align_left))
            if default_stmt is not '':
                printer.println('%s[k] = (%s)? %s: *((float*)(&temp_%s));'
                            % (dst, default_stmt, str(default_value), dst))
            else:
                printer.println('%s[k] = *((float*)(&temp_%s));'
                                % (dst, dst))


    def print_data_movement(self, printer: Printer):
        ''' Print aata flow along the Line Buffer'''
        for item1, item2 in zip(self.lineBuffer.buffer_flow, self.lineBuffer.buffer_flow[1:]):
            temp = ''
            if type(item1) != Block:
                temp += item1.name + ' << '
            else:
                temp += item1.name + ' = '

            if type(item2) != Block:
                temp += item2.name + '.read()'
            else:
                temp += item2.name
            temp += ';'
            printer.println(temp)

        printer.println()
        printer.println('unsigned int idx_%s = %s + (i + %s);'
                        % (self.var_name, self.lineBuffer.min_block_offset, self.lineBuffer.buffer_flow[-1].index + 1))
        printer.println('%s = HLS_REG(%s[idx_%s]);'
                        % (self.lineBuffer.buffer_flow[-1].name, self.var_name, self.var_name))

    def print_data_movement_from_stream(self, printer: Printer):
        ''' Print aata flow along the Line Buffer'''
        for item1, item2 in zip(self.lineBuffer.buffer_flow, self.lineBuffer.buffer_flow[1:]):
            temp = ''
            if type(item1) != Block:
                temp += item1.name + ' << '
            else:
                temp += item1.name + ' = '

            if type(item2) != Block:
                temp += item2.name + '.read()'
            else:
                temp += item2.name
            temp += ';'
            printer.println(temp)

        printer.println()
        printer.println('%s = %s.read();'
                        % (self.lineBuffer.buffer_flow[-1].name, self.var_name))


    def print_pop_out(self, printer:Printer):
        '''Print Pop Out all stream buffer'''
        for stream_buffer in self.lineBuffer.streams:
            printer.println('INTERFACE_WIDTH popout_%s;'
                            % (stream_buffer.name))
            # with printer.for_('int i = 0', 'i < %s' % stream_buffer.length, 'i++'):
            #     printer.println('#pragma HLS pipeline II=1')
            #     printer.println('%s >> popout_%s;'
            #                     % (stream_buffer.name, stream_buffer.name))
            printer.println('while(!%s.empty()){' % stream_buffer.name)
            printer.do_indent()
            printer.println('%s >> popout_%s;'
                                % (stream_buffer.name, stream_buffer.name))
            printer.un_indent()
            printer.println('}')


    def print_c_buffer_def(self, printer:Printer):
        printer.println('unsigned int %s_buffer_size = GRID_COLS*PART_ROWS + %d*WIDTH_FACTOR'
                        ' + (TOP_APPEND+BOTTOM_APPEND)*WIDTH_FACTOR*(STAGE_COUNT-1)'
                        ' + (OVERLAP_TOP_OVERHEAD + OVERLAP_BOTTOM_OVERHEAD)*WIDTH_FACTOR;' %
                        (self.var_name, self.lineBuffer.min_block_offset + self.lineBuffer.max_block_offset))
        printer.println('std::vector<std::vector<float, aligned_allocator<float> > > %ss;' % self.var_name)
        with printer.for_('int i = 0', 'i < KERNEL_COUNT', 'i++'):
            printer.println('%ss.emplace_back(%s_buffer_size, 0);' % (self.var_name, self.var_name))

    def print_c_buffer_init(self, printer:Printer):
        printer.println('read_%s_buffer(%ss);' % (self.var_name, self.var_name))

    def print_c_buffer_allocate(self, printer:Printer):
        printer.println('std::vector<cl_mem_ext_ptr_t> ptr_%ss(KERNEL_COUNT);' % self.var_name)
        printer.println('std::vector<cl::Buffer> device_%ss;' % self.var_name)

        with printer.for_('int i = 0', 'i < KERNEL_COUNT', 'i++'):
            printer.println('ptr_%ss[i].obj = %ss[i].data();' % (self.var_name, self.var_name))
            printer.println('ptr_%ss[i].param = 0;' % self.var_name)
            printer.println('ptr_%ss[i].flags = pc[hbm_offset_%s[i]];' % (self.var_name, self.var_name))
            printer.println()
            printer.println('OCL_CHECK(err, device_%ss.emplace_back(context, ' 
                            'CL_MEM_USE_HOST_PTR | CL_MEM_EXT_PTR_XILINX | CL_MEM_READ_WRITE, ' % self.var_name)
            printer.println('\t%s_buffer_size*sizeof(float), &ptr_%ss[i], &err));' % (self.var_name, self.var_name))

    def print_c_load_func(self, printer: Printer):
        printer.println('void read_%s_buffer(std::vector<std::vector<float, aligned_allocator<float> > >& %ss) {'
                        % (self.var_name, self.var_name))
        printer.do_indent()

        printer.println('const std::string %s_path("../data/%s.data");' % (self.var_name, self.var_name))
        printer.println('std::ifstream %s_file(%s_path);' % (self.var_name, self.var_name))

        printer.println()
        printer.println('std::cout << "Start loading %s" << std::endl;' % (self.var_name))

        printer.println()

        with printer.for_('int i = 0', 'i < KERNEL_COUNT', 'i++'):

            with printer.ifel_('i == 0'):
                printer.println('fill_buffer(%ss[i].data() + %d*WIDTH_FACTOR/*min_block_offsets*/ + TOP_APPEND*WIDTH_FACTOR*(STAGE_COUNT-1) '
                                '+ OVERLAP_TOP_OVERHEAD*WIDTH_FACTOR,'
                                ' %s_file, 0, GRID_COLS*PART_ROWS + %d*WIDTH_FACTOR/*max_block_offsets*/ + BOTTOM_APPEND*WIDTH_FACTOR*(STAGE_COUNT-1) '
                                '+ OVERLAP_BOTTOM_OVERHEAD*WIDTH_FACTOR);'
                                % (self.var_name, self.lineBuffer.min_block_offset,
                                   self.var_name, self.lineBuffer.max_block_offset))

            with printer.elifel_('i == KERNEL_COUNT - 1'):
                printer.println('fill_buffer(%ss[i].data(), %s_file, GRID_COLS*PART_ROWS*i - %d*WIDTH_FACTOR/*min_block_offsets*/ '
                                '- TOP_APPEND*WIDTH_FACTOR*(STAGE_COUNT-1) - OVERLAP_TOP_OVERHEAD*WIDTH_FACTOR, '
                                'GRID_COLS*PART_ROWS + %d*WIDTH_FACTOR/*min_block_offsets*/ + TOP_APPEND*WIDTH_FACTOR*(STAGE_COUNT-1) '
                                '+ OVERLAP_TOP_OVERHEAD*WIDTH_FACTOR);'
                                % (self.var_name, self.var_name, self.lineBuffer.min_block_offset,
                                   self.lineBuffer.min_block_offset))

            with printer.else_():
                printer.println('fill_buffer(%ss[i].data(), %s_file, GRID_COLS*PART_ROWS*i - %d*WIDTH_FACTOR/*min_block_offsets*/ '
                                '- TOP_APPEND*WIDTH_FACTOR*(STAGE_COUNT-1) - OVERLAP_TOP_OVERHEAD, '
                                'GRID_COLS*PART_ROWS + %d*WIDTH_FACTOR + (TOP_APPEND+BOTTOM_APPEND)*WIDTH_FACTOR*(STAGE_COUNT-1) '
                                '+ (OVERLAP_TOP_OVERHEAD + OVERLAP_BOTTOM_OVERHEAD)*WIDTH_FACTOR);'
                                % (self.var_name, self.var_name, self.lineBuffer.min_block_offset,
                                   self.lineBuffer.max_block_offset + self.lineBuffer.min_block_offset))

        printer.println()

        printer.println('%s_file.close();' % self.var_name)
        printer.un_indent()
        printer.println('}')


class OutputBufferConfig:
    def __init__(self, var_name, min_block_offset, max_block_offset):
        self.var_name = var_name
        self.min_block_offset = min_block_offset
        self.max_block_offset = max_block_offset

    def print_c_buffer_def(self, printer:Printer):
        printer.println('unsigned int %s_buffer_size = GRID_COLS*PART_ROWS + %d*WIDTH_FACTOR'
                        ' + (TOP_APPEND+BOTTOM_APPEND)*WIDTH_FACTOR*(STAGE_COUNT-1)'
                        ' + (OVERLAP_TOP_OVERHEAD + OVERLAP_BOTTOM_OVERHEAD)*WIDTH_FACTOR;' %
                        (self.var_name, self.min_block_offset + self.max_block_offset))
        printer.println('std::vector<std::vector<float, aligned_allocator<float> > > %ss;' % self.var_name)
        with printer.for_('int i = 0', 'i < KERNEL_COUNT', 'i++'):
            printer.println('%ss.emplace_back(%s_buffer_size, 0);' % (self.var_name, self.var_name))

    def print_c_buffer_allocate(self, printer:Printer):
        printer.println('std::vector<cl_mem_ext_ptr_t> ptr_%ss(KERNEL_COUNT);' % self.var_name)
        printer.println('std::vector<cl::Buffer> device_%ss;' % self.var_name)

        with printer.for_('int i = 0', 'i < KERNEL_COUNT', 'i++'):
            printer.println('ptr_%ss[i].obj = %ss[i].data();' % (self.var_name, self.var_name))
            printer.println('ptr_%ss[i].param = 0;' % self.var_name)
            printer.println('ptr_%ss[i].flags = pc[hbm_offset_%s[i]];' % (self.var_name, self.var_name))
            printer.println()
            printer.println('OCL_CHECK(err, device_%ss.emplace_back(context, ' 
                            'CL_MEM_USE_HOST_PTR | CL_MEM_EXT_PTR_XILINX | CL_MEM_READ_WRITE, ' % self.var_name)
            printer.println('\t%s_buffer_size*sizeof(float), &ptr_%ss[i], &err));' % (self.var_name, self.var_name))
