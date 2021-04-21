"""
Test input and output arguments of sed.apply (filenames, files or streams)
"""

import os
import sys
import io
from PythonSed import Sed


INPUT_STRING = 'In Xanadu did Kubla Khan\n'
OUTPUT_STRING = 'In XANadu did Kubla KhAN\n'
SCRIPT = '/X/s/an/AN/gp'
INPUT_FILENAME = 'test-tmp-in.txt'
OUTPUT_FILENAME = 'test-tmp-out.txt'

def main():
    try:
        sed = Sed()
        sed.no_autoprint = True
        sed.regexp_extended = False
        sed.debug = 0
        sed.load_string(SCRIPT)
    
        with open(INPUT_FILENAME, 'wt') as f:
            print(INPUT_STRING, file=f, end='')
            
        # input and ouput arguments are filenames
        sed.apply(INPUT_FILENAME, OUTPUT_FILENAME)
        exit_code = sed.exit_code

        with open(OUTPUT_FILENAME) as f:
            s = f.readline()
        if s != OUTPUT_STRING:
            print('Input and output arguments are filenames:')
            print('|' + s + '|')
            print('|' + OUTPUT_STRING + '|')
            exit_code += 2
    
        # input and ouput arguments are files
        with open(INPUT_FILENAME) as f_in, open(OUTPUT_FILENAME, 'wt') as f_out:
            sed.apply(f_in, f_out)
        with open(OUTPUT_FILENAME) as f:
            s = f.readline()
        if s != OUTPUT_STRING:
            print('Input and output arguments are file objects:')
            print('|' + s + '|')
            print('|' + OUTPUT_STRING + '|')
            exit_code += 4
    
        # input and output arguments are streams
        with io.StringIO(INPUT_STRING) as stream_in, io.StringIO() as stream_out:
            sed.apply(stream_in, stream_out)
            s = stream_out.getvalue()
        if s != OUTPUT_STRING:
            print('Input and output arguments are stream objects:')
            print('|' + s + '|')
            print('|' + OUTPUT_STRING + '|')
            exit_code += 8
    
    finally:
        if os.path.exists(INPUT_FILENAME):
            os.remove(INPUT_FILENAME)
        if os.path.exists(OUTPUT_FILENAME):
            os.remove(OUTPUT_FILENAME)

    if exit_code==0:
        # ok
        print('OK')
        sys.exit(0)
    else:
        sys.exit(exit_code)

main()