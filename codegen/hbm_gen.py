import logging
import math
from copy import copy

from codegen import codegen_utils

_logger = logging.getLogger().getChild(__name__)


def hbm_files_gen(stencil, head_file, cfg_file):
    _logger.info('generate hbm config head code as %s', head_file.name)
    printer = codegen_utils.Printer(head_file)

    all_vars = copy(stencil.input_vars)
    all_vars.append(stencil.output_var)

    interval = 32 / stencil.kernel_count

    if interval < len(all_vars):
        _logger.error('required buffer num is out of bound, consider use less kernels')
        exit(1)

    '''different heuristic schedules for overlap and streaming mode'''
    hbm_schedules = {}
    slr_schedules = []
    for var in all_vars:
        hbm_schedules[var] = []

    if stencil.iterate == 1 or stencil.boarder_type == 'overlap':
        for i in range(0, stencil.kernel_count):
            slr_schedules.append(i % 3)
            j = 0
            for var in all_vars:
                hbm_schedules[var].append(math.floor(i*interval)+j)
                j += 1
    else:
        kernel_per_slr = math.ceil(stencil.kernel_count/3)
        for i in range(0, stencil.kernel_count):
            slr_schedules.append(math.floor(i/kernel_per_slr))
            j = 0
            for var in all_vars:
                if slr_schedules[-1] == 1:
                    hbm_to_assign = math.floor(interval * (slr_schedules[-1] +
                                                           (kernel_per_slr - i % kernel_per_slr - 1) * 3)) + j
                else:
                    hbm_to_assign = math.floor(interval * (slr_schedules[-1] + (i % kernel_per_slr) * 3)) + j
                hbm_schedules[var].append(hbm_to_assign)
                j += 1

    '''hbm_config.h generation'''
    printer.println('#ifndef HBM_CONFIG_H')
    printer.println('#define HBM_CONFIG_H')

    for var in all_vars:
        printer.println('int hbm_offset_%s[%s] = {%s};'
                        % (var, stencil.kernel_count,
                           ', '.join(
                               '%s' % (hbm_schedules[var][k]) for k in range(0, stencil.kernel_count))))

    printer.println('#endif')

    '''settings.cfg generation'''
    _logger.info('generate hbm config code as %s', cfg_file.name)
    printer = codegen_utils.Printer(cfg_file)

    printer.println('[connectivity]')

    if stencil.iterate == 1 or stencil.boarder_type == 'overlap':
        printer.println('nk=unikernel:%s' % stencil.kernel_count)
        printer.println()

        for i in range(0, stencil.kernel_count):
            for var in all_vars:
                printer.println('sp=unikernel_%s.%s:HBM[%s]'
                                % (i + 1, var, hbm_schedules[var][i]))

        printer.println()

        for i in range(0, stencil.kernel_count):
            printer.println('slr=unikernel_%s:SLR%s' % (i + 1, slr_schedules[i]))

    else:
        printer.println('nk=midkernel:%s:%s' % (stencil.kernel_count - 2,
                                                '.'.join('midkernel_%s' % i for i in range(2, stencil.kernel_count))))
        printer.println()

        for i in range(0, stencil.kernel_count):
            for var in all_vars:
                if i == 0:
                    printer.println('sp=upkernel_1.%s:HBM[%s]'
                                    % (var, hbm_schedules[var][i]))
                elif i == stencil.kernel_count - 1:
                    printer.println('sp=downkernel_1.%s:HBM[%s]'
                                    % (var, hbm_schedules[var][i]))
                else:
                    printer.println('sp=midkernel_%s.%s:HBM[%s]'
                                    % (i + 1, var, hbm_schedules[var][i]))

        printer.println()

        # for i in range(0, stencil.kernel_count):
        #     if i == 0:
        #         printer.println('slr=upkernel_1:SLR0')
        #     elif i == stencil.kernel_count - 1:
        #         printer.println('slr=downkernel_1:SLR%s' % slr_schedules[i])
        #     else:
        #         printer.println('slr=midkernel_%s:SLR%s' % (i+1, slr_schedules[i]))

        # printer.println()

        # printer.println('sc=upkernel_1.stream_to:midkernel_2.stream_from_up\n'
        #                 'sc=midkernel_2.stream_to_up:upkernel_1.stream_from\n')

        # for i in range(2, stencil.kernel_count - 1):
        #     printer.println('sc=midkernel_%s.stream_to_down:midkernel_%s.stream_from_up\n'
        #                     'sc=midkernel_%s.stream_to_up:midkernel_%s.stream_from_down\n'
        #                     % (i, i + 1, i + 1, i))

        # printer.println('sc=midkernel_%s.stream_to_down:downkernel_1.stream_from\n'
        #                 'sc=downkernel_1.stream_to:midkernel_%s.stream_from_down\n'
        #                 % (stencil.kernel_count - 1, stencil.kernel_count - 1))
