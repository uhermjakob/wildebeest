#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
Pytest for wb_analysis.py
"""

import os
import sys
import wildebeest.wb_analysis as wb_ana

example = int(sys.argv[1]) if len(sys.argv) > 1 else 1
test_data_dir = os.path.join(os.path.dirname(sys.argv[0]), 'data')

s1 = "Hеllο!"  # string mischievously contains a mix of Latin, Greek and Cyrillic characters
s2 = "Tschüß"  # German for 'Bye'

if example == 2:
    wb = wb_ana.process(strings=[s1, s2])
    print(wb.analysis)  # print analysis object (nested dictionary)
elif example == 3:
    wb = wb_ana.process(in_file=f'{test_data_dir}/corpus.txt')
    print(wb.analysis)
elif example == 4:
    with open(f'{test_data_dir}/out.txt', 'w') as out, open(f'{test_data_dir}/out.json', 'w') as json:
        wb_ana.process(in_file=f'{test_data_dir}/corpus.txt', pp_output=out, json_output=json)
else:
    wb = wb_ana.process(string=s1)
    wb.pretty_print(sys.stdout)  # pretty-print with OVERVIEW and DETAIL to STDOUT
