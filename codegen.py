import argparse
import logging
import os
import sys

import textx

import core
import dsl
from dsl import ir
import codegen

logging.basicConfig(level=logging.WARNING,
                    format='%(levelname)s:%(name)s:%(lineno)d: %(message)s')
logger = logging.getLogger().getChild(os.path.basename(__file__))

def main():
    parser = argparse.ArgumentParser(
        prog='test_textx',
        description='Test dsl grammar with a input DSL test file'
    )
    parser.add_argument(
        '--src',
        type=str,
        dest='test_file'
    )

    logging.getLogger().setLevel(logging.DEBUG)
    logger.info('Begin Logging:')

    ''' Parse input program'''
    args = parser.parse_args()
    if args.test_file == None:
        logger.info('Lack of file input')
    else:
        logger.info('Test File: %s', args.test_file)

    dsl_mm = textx.metamodel_from_str(dsl.lan, classes=ir.CLASSES)
    dsl_m = dsl_mm.model_from_file(args.test_file)

    logger.info('Program successfully parsed:\n %s',
                str(dsl_m).replace('\n', '\n '))

    stencil = core.Stencil(
        iterate=dsl_m.iterate,
        boarder_type=dsl_m.boarder_type,
        kernel_count=dsl_m.kernel_count,
        repeat_count=dsl_m.repeat_count,
        app_name=dsl_m.app_name,
        size=dsl_m.size,
        scalar_stmts=dsl_m.scalar_stmts,
        input_stmts=dsl_m.input_stmts,
        local_stmts=dsl_m.local_stmts,
        output_stmt=dsl_m.output_stmt
    )

    codegen.hls_codegen(stencil)

if __name__ == '__main__':
    main()