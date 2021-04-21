"""
Test input and output arguments of sed.apply (filenames, files or streams)
"""

import os
import sys
from PythonSed import Sed

INPUT_DATA="""\
this is text
to be edited
inplace, to test that feature.
"""

OUTPUT_DATA="""\
this is text
to be edited and checked
afterwards for a test of in-place editing.
"""

SED_SCRIPT="""\
3s/edited/& and checked/
4c afterwards for a test of in-place editing.
"""

SED_SCRIPT2="""\
3s/edited/& and checked/
$c afterwards for a test of in-place editing.
"""

INPUT_FILENAME_1 = 'test-tmp-in-1.txt'
INPUT_FILENAME_2 = 'test-tmp-in-2.txt'
OUTPUT_FILENAME  = 'test-tmp-out.txt'

def remove_file(filename):
    if os.path.exists(filename):
        os.remove(filename)

def main():
    exit_code = test_inplace(SED_SCRIPT,'.bkup',0)
    if exit_code==0:
        exit_code += test_inplace(SED_SCRIPT2,'*.bkup',2)

    if exit_code==0:
        # ok
        print('OK')
        sys.exit(0)
    else:
        sys.exit(exit_code)
    
    
def test_inplace(script,inplace,debug):
    try:
        sed = Sed()
        sed.no_autoprint = False
        sed.regexp_extended = False
        sed.debug = debug
        sed.load_string(script)
        sed.in_place = inplace
        
        remove_file(INPUT_FILENAME_1+'.bkup')
        remove_file(INPUT_FILENAME_2+'.bkup')
        remove_file(OUTPUT_FILENAME)
        
        with open(INPUT_FILENAME_1, 'wt') as f:
            print(INPUT_FILENAME_1, file=f)
            print(INPUT_DATA, file=f, end='')
    
        with open(INPUT_FILENAME_2, 'wt') as f:
            print(INPUT_FILENAME_2, file=f)
            print(INPUT_DATA, file=f, end='')
                
        # input and ouput arguments are filenames
        sed.apply( [ INPUT_FILENAME_1, INPUT_FILENAME_2 ], OUTPUT_FILENAME)
        
        exit_code = sed.exit_code
        if os.path.exists(OUTPUT_FILENAME):
            with open(OUTPUT_FILENAME,'rt') as f:
                s = f.read()
            if len(s)>0:
                print('The command should have not printed anything but output the following:')
                print(s)
                exit_code += 2
    
        with open(INPUT_FILENAME_1,'rt') as f:
            s = f.read()
        if s!=INPUT_FILENAME_1+'\n'+OUTPUT_DATA:
            print('---- The input file 1 contains:')
            print(s)
            print('---- instead of ----')
            print(INPUT_FILENAME_1+'\n'+OUTPUT_DATA)
            exit_code += 4
                
        with open(INPUT_FILENAME_2,'rt') as f:
            s = f.read()
        if s!=INPUT_FILENAME_2+'\n'+OUTPUT_DATA:
            print('---- The input file 2 contains:')
            print(s)
            print('---- instead of ----')
            print(INPUT_FILENAME_2+'\n'+OUTPUT_DATA)
            exit_code += 8
            
        if not (os.path.exists(INPUT_FILENAME_1+'.bkup') and os.path.exists(INPUT_FILENAME_2+'.bkup')):
            print('Backup-files missing')
            exit_code += 16
           
    finally:
        remove_file(INPUT_FILENAME_1)
        remove_file(INPUT_FILENAME_2)
        remove_file(INPUT_FILENAME_1+'.bkup')
        remove_file(INPUT_FILENAME_2+'.bkup')
        remove_file(OUTPUT_FILENAME)

    return exit_code

if __name__=='__main__':
    main()
    