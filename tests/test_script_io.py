"""
Test input and output arguments of sed.apply (filenames, files or streams)
"""

import sys
import io
from PythonSed import Sed, SedException


INPUT_STRING = 'In Xanadu did Kubla Khan'
OUTPUT_STRING = 'In XANadu did Kubla KhAN'
SCRIPT = '/X/s/an/AN/gp'
INPUT_FILENAME = 'tmp.txt'
OUTPUT_FILENAME = 'tmp2.txt'


def main():
    sed = Sed()
    sed.no_autoprint = True
    sed.regexp_extended = False
    sed.load_string(SCRIPT)

    with open(INPUT_FILENAME, 'wt') as f:
        print(INPUT_STRING, file=f)

    # input and ouput arguments are filenames
    sed.apply(INPUT_FILENAME, OUTPUT_FILENAME)
    with open(OUTPUT_FILENAME) as f:
        s = f.readline().strip()
    if s != OUTPUT_STRING:
        sys.exit(1)

    # input and ouput arguments are files
    with open(INPUT_FILENAME) as f_in, open(OUTPUT_FILENAME, 'wt') as f_out:
        sed.apply(f_in, f_out)
    with open(OUTPUT_FILENAME) as f:
        s = f.readline().strip()
    if s != OUTPUT_STRING:
        sys.exit(2)

    # input and ouput arguments are streams
    with io.StringIO(INPUT_STRING) as stream_in, io.StringIO() as stream_out:
        sed.apply(stream_in, stream_out)
        s = stream_out.getvalue().strip()
    if s != OUTPUT_STRING:
        print('|' + s + '|')
        print('|' + OUTPUT_STRING + '|')
        sys.exit(3)

    # ok
    sys.exit(0)


main()