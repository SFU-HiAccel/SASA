#!/usr/bin/python3
import os
import re
import math

def parse_utlization(file_name):
  with open(file_name, 'r') as f:
    lines = f.readlines()
  
  pattern = "The total area of the design:"
  for idx, line in enumerate(lines):
    match = re.search(pattern, line)
    if match:
      start_line_idx = idx + 1
      break

  pe_num = 100
  for i in range(5):
    target_line = lines[start_line_idx + i].split("=")
    percent_string = target_line[1]
    resource_rate = float(percent_string.split('%')[0])
    if resource_rate != 0.0:
      current_num = int(70 / resource_rate)
      print(current_num)
    else:
      current_num = 100
    if current_num < pe_num:
      pe_num = current_num
  
  return (pe_num)
    
# os.system('cp stencil.dsl single.dsl')
with open("single.dsl", 'a') as f:
  f.writelines(['COUNT: 1 \n', 'REPEAT:1\n', 'BOARDER:overlap\n'])

with open("single.dsl", 'r') as f:
  lines = f.readlines()

iteration_idx = 0
input_idx = 0
for idx, line in enumerate(lines):
  iteration_match = re.search('ITERATE', line)
  input_match = re.search('input', line)
  if iteration_match:
    iteration_idx = idx
  if input_match:
    input_idx = idx
  
iteration_data = lines[iteration_idx].split(':')[1]
input_data = lines[input_idx].split('(')[1]

iteration_num = int(iteration_data)
row = int(input_data.split(',')[0])
col = int(input_data.split(',')[1].split(')')[0])
print(iteration_num)
print(row)
print(col)
# os.system('python3 codegen.py --src ./single.dsl')

# os.system('chmod 755 tapa_test.sh')
# os.system('./tapa_test.sh')
os.system('cp tapa_run/autobridge/autobridge*.log ./autobridge.log')
pe_num = parse_utlization('autobridge.log')

os.system('cp stencil.dsl complete.dsl')
stage_num = math.floor(pe_num / 3)
with open("complete.dsl", 'a') as f:
  f.writelines(['COUNT: 3 \n', 'REPEAT:%d\n' % stage_num, 'BOARDER:streaming\n'])

os.system('./tapa.sh')

os.system('chmod 755 unikernel.hw_generate_bitstream.sh')
os.system('./unikernel.hw_generate_bitstream.sh')

# not_found = True
# while not_found:
#   if pe_num > iteration_num:

#   else:
#     lt = ceil((row + 1 * (pe_num - 1) * col) / 16) * ceil(iteration_num / pe_num)

# os.system('tapac -o unikernel.hw.xo ./unikernel.cpp --platform xilinx_u280_xdma_201920_3 --top unikernel --work-dir tapa_run --connectivity settings.cfg --enable-floorplan --floorplan-output constraint.tcl --enable-hbm-binding-adjustment --enable-synth-util')
# os.system('./tapa.sh')

