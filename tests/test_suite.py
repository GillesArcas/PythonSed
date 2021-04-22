#!/usr/bin/env python
from __future__ import print_function

BRIEF = """\
test-suite.py - unit testing utility for sed - sed.godrago.net\
"""

VERSION = '1.00'

USAGE = """\
test-suite.py [@]<file> [test-ref] [-b binary] [-x exclude-file]
<file> may be:
    - a text file implementing tests, cf. unit.suite
    - a folder containing scripts and data, cf. testsuite\\
    - a batch reference, if prefixed with @, containing file names or
      folder names cf. all_tests.suites
"""

LICENSE = """\
Copyright (c) 2014 Gilles Arcas-Luque (gilles dot arcas at gmail dot com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import sys
import os
import re
import argparse
import subprocess
import time
from PythonSed import Sed, SedException

if sys.version_info[0]==2:
    OPEN_ARGS = {}
else:
    from io import open as open
    OPEN_ARGS = { 'encoding': 'latin-1'}

# -- Base class for tests ----------------------------------------------------


class BaseTest:
    def __init__(self):
        self.script = None
        self.title = None
        self.input = None
        self.result = None
        self.wgood = None
        self.scriptname = None
        self.inputname = None
        self.goodname = None
        self.res_output = None
        self.run_output = []
        self.no_autoprint = None
        self.regexp_extended = None
        self.current_dir =  None
        self.error_expected = False

    def run(self, binary=None, debug=False):

        if binary is None:
            self.run_output = run_python_sed(self.scriptname, self.inputname,
                                             self.no_autoprint,
                                             self.regexp_extended,debug)
        else:
            self.run_output = run_binary_sed(self.scriptname, self.inputname,
                                             self.no_autoprint,
                                             self.regexp_extended,debug,
                                             binary)

    def checktest(self, ntest, scriptname, wgood):
        # common check routine
        # derived class must change directory if necessary

        if self.error_expected:
            ref_output = []
        else:
            try:
                with open(self.goodname,'rt',**OPEN_ARGS) as f:
                    ref_output = [line.strip('\n\r') for line in f.readlines()]
            except IOError:
                print('error reading %s' % self.goodname)
                sys.exit(1)
            except:
                raise

        if self.run_output is None:
            run_output = []
        else:
            run_output = []
            for line in self.run_output:
                run_output.extend([x.strip('\r') for x in line.split('\n')])
                ##run_output.extend(line.splitlines())
                ##run_output.extend([x.strip('\r') for x in line.splitlines()])

        return checktest(ntest, scriptname, ref_output, run_output, wgood)

    def ignore(self, testnum):
        print('Test %3d ignored: %s' % (testnum, self.title))

    def postproc(self):
        pass


# -- Collection of tests in suite file ---------------------------------------


class SuiteTest(BaseTest):
    # test found in suite file

    def __init__(self, title, script, inputlines, resultlines):
        BaseTest.__init__(self)

        self.scriptname = 'test-tmp-script.sed'
        self.inputname = 'test-tmp-script.inp'
        self.goodname  = 'test-tmp-script.good'
        self.flagsname = None

        # script, input and result may be empty. In that case, the
        # previously defined entity is used.
        self.title  = title[0]
        self.script = '' if script == [] else script
        self.input  = '' if inputlines == [] else inputlines
        self.result = '' if resultlines == [] else resultlines
        self.error_expected = self.result is None

    def prepare(self):

        # write script
        with open(self.scriptname, 'wt', **OPEN_ARGS) as f:
            for line in self.script:
                print(line, file=f)

        # write input file
        with open(self.inputname, 'wt', **OPEN_ARGS) as f:
            for line in self.input:
                print(line, file=f)

        # write expected result
        if self.error_expected:
            pass
        else:
            with open(self.goodname, 'wt', **OPEN_ARGS) as f:
                for line in self.result:
                    print(line, file=f)

        # set autoprint flag (set later on when reading first line of script)
        self.no_autoprint = None

        # handle #r extended flag
        # n must appear first to stay compatible with standard
        self.regexp_extended = False
        line1 = self.script[0]
        if line1.startswith('#r') or line1.startswith('#nr'):
            self.regexp_extended  = True

        return True

    #def run(self, binary=None):
    #   inherited

    def check(self, ntest, scriptname):

        return BaseTest.checktest(self, ntest, scriptname, [])


# -- Collection of tests in directory ----------------------------------------


class FolderTest(BaseTest):
    # test found in folder

    def __init__(self, scriptname, folder):
        BaseTest.__init__(self)

        self.scriptname = scriptname
        self.inputname = scriptname.replace('.sed', '.inp')
        self.goodname  = scriptname.replace('.sed', '.good')
        self.flagsname = scriptname.replace('.sed', '.flags')

        self.folder = folder
        self.title = scriptname
        self.error_expected = False

    def prepare(self):
        self.current_dir = os.getcwd()
        os.chdir(self.folder)

        if not os.path.isfile(self.inputname):
            print('%s: input file not found' % self.inputname)
            os.chdir(self.current_dir)
            return False

        if not os.path.isfile(self.goodname):
            # expected result file is missing when waiting for exception
            self.error_expected = True

        # read flags file if any
        self.no_autoprint = False
        self.regexp_extended = False
        if os.path.isfile(self.flagsname):
            with open(self.flagsname,'rt',**OPEN_ARGS) as f:
                for line in f:
                    self.no_autoprint = self.no_autoprint or ('-n' in line)
                    self.regexp_extended = self.regexp_extended or ('-r' in line)

        # find list of wgood files (files written by w command or w switch)
        wgood = os.listdir('.')
        self.wgood = [x for x in wgood if self.scriptname.replace('.sed', '.wgood') in x]

        # delete wout files if any
        for fgood in self.wgood:
            wout = fgood.replace('.wgood', '.wout')
            if os.path.isfile(wout):
                os.remove(wout)

        return True

    #def run(self, binary=None):
    #   inherited

    def check(self, ntest, scriptname):

        res = BaseTest.checktest(self, ntest, scriptname, self.wgood)
        return res

    def postproc(self):
        os.chdir(self.current_dir)


# -- Helpers -----------------------------------------------------------------


def run_python_sed(scriptname, inputfile, no_autoprint, regexp_extended, debug):
    sed = Sed()
    sed.no_autoprint = no_autoprint
    sed.regexp_extended = regexp_extended
    sed.encoding = 'latin-1'
    if debug:
        sed.debug = 2
        
    try:
        # all loading methods must give the same result
        mode = 1 # 1, 2, 3

        if mode == 1:
            sed.load_script(scriptname)
        elif mode == 2:
            with open(scriptname,'rt',**OPEN_ARGS) as f:
                string = ''.join(f.readlines())
            sed.load_string(string)
        elif mode == 3:
            with open(scriptname,'rt',**OPEN_ARGS) as f:
                string_list = f.readlines()
            sed.load_string_list(string_list)
        else:
            raise Exception()

        return ''.join(sed.apply(inputfile, None)).split('\n')
    except SedException as e:
        print(e.message,file=sys.stderr)
        return None
    except:
        raise

def run_binary_sed(scriptname, inputfile, no_autoprint, regexp_extended,
                   binary, debug):
    template = r'%s %s %s %s -f %s %s'
    command_line = template % (binary,
                               '-n' if no_autoprint else '',
                               '-r' if regexp_extended else '',
                               '-d' if debug else '',
                               scriptname,
                               inputfile)
    try:
        output = check_output(command_line, shell=True)

        # ascii utf-8 iso8859_15 latin_1
        #output = output.decode('latin_1', errors='replace')
        if sys.version_info[0] == 2:
            pass
        else:
            output = output.decode('latin-1', errors='replace')

        output = output.split('\n')
        #output = output.splitlines()
        return output
    except subprocess.CalledProcessError as e:
        print(e)
        return None
    except:
        raise

def checktest(testnum, testname, ref_output, run_output, wgood):
    # compare expected and obtained results

    # outputs may be None if exception, will be compared as list
    if run_output is None:
        run_output = []
    if ref_output is None:
        ref_output = []

    # compare outputs
    result, diff = list_compare('ref', 'out', ref_output, run_output)

    # compare files written by w command or w switch
    for fgood in wgood:
        wout = fgood.replace('.wgood', '.wout')
        result2, diff2 = file_compare(fgood, wout)
        result = result and result2
        diff.extend(diff2)

    # feedback
    if result:
        print('Test %3d success: %s' % (testnum, testname))
    else:
        print('Test %3d failure: %s' % (testnum, testname))
        for x in diff:
            print(str(x))

    return result

def list_compare(tag1, tag2, list1, list2):

    max_lst_len = max(len(list1), len(list2))
    if max_lst_len==0:
        return True,[]
    
    max_txt_len=max(list(len(txt) for txt in (list1+list2))+[len(tag1),len(tag2)])
    
    # make sure both lists have same length
    list1.extend([''] * (max_lst_len - len(list1)))
    list2.extend([''] * (max_lst_len - len(list2)))

    diff = list()
    res = True
    diff.append('| No | ? | {tag1:<{txtlen}.{txtlen}s} | {tag2:<{txtlen}.{txtlen}s} |'
                .format(tag1=tag1, tag2=tag2, txtlen=max_txt_len))
    for i, (x, y) in enumerate(zip(list1, list2)):
        
        diff.append('| {idx:>2d} | {equal:1.1s} | {line1:<{txtlen}.{txtlen}s} | {line2:<{txtlen}.{txtlen}s} |'
                     .format(idx=i+1,
                             equal=(' ' if x==y else '*'),
                             txtlen=max_txt_len,
                             line1=x,
                             line2=y))
        res = res and x==y
    return res, diff

def file_compare(fn1, fn2):
    with open(fn1,'rt',**OPEN_ARGS) as f:
        lines1 = [line.strip('\n') for line in f.readlines()]
    with open(fn2,'rt',**OPEN_ARGS) as f:
        lines2 = [line.strip('\n') for line in f.readlines()]
    return list_compare(fn1, fn2, lines1, lines2)

def check_output(*popenargs, **kwargs):
    # maintain compatibility with 2.6
    # https://gist.github.com/edufelipe/1027906
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
            error = subprocess.CalledProcessError(retcode, cmd)
            error.output = output
            raise error
    return output


# -- Loading test suites -----------------------------------------------------


def load_testsuite(testsuite):
    # dispatch on test suite type

    if testsuite[0] == '@':
        if os.path.isfile(testsuite[1:]):
            all_tests = load_testsuite_batch(testsuite[1:])
        else:
            all_tests = list()
            print('Test suite not found:', testsuite)
    elif testsuite.endswith('.suite') and os.path.isfile(testsuite):
        all_tests = load_testsuite_file(testsuite)
    elif os.path.isdir(testsuite):
        all_tests = load_testsuite_folder(testsuite)
    else:
        all_tests = list()
        print('Test suite not found:', testsuite)

    return all_tests

def load_testsuite_file(testsuite):
    # testsuite is a suite file

    def getsection(lines, i, delim):
        i += 1
        i0 = i
        while i < len(lines) and not lines[i].startswith(delim):
            i += 1
        if i == len(lines):
            print('Test not complete')
            return None, i
        else:
            return lines[i0:i], i

    tests = list()

    with open(testsuite,'rt',**OPEN_ARGS) as f:
        lines = [line.rstrip('\r\n') for line in f.readlines()]

    i = 0
    while i < len(lines):
        # find first delimiter
        while i < len(lines) and not re.match(r'(\S)\1\1', lines[i]):
            i += 1
        if i == len(lines):
            break
        delim = lines[i][0:3]

        title,i = getsection(lines, i, delim)
        script,i = getsection(lines, i, delim)
        inputlines,i = getsection(lines, i, delim)
        resultlines,i = getsection(lines, i, delim)
        if resultlines == ['???']:
            resultlines = None

        i += 1

        tests.append(SuiteTest(title, script, inputlines, resultlines))
        test = tests[-1]
        index = len(tests) - 1

        if test.script == '':
            if index == 0:
                print('test-suite error: empty script on first test')
                sys.exit(1)
            else:
                test.script = tests[index-1].script

        if test.input == '':
            if index == 0:
                print('test-suite error: empty input on first test')
                sys.exit(1)
            else:
                test.input = tests[index-1].input

        if test.result == '':
            if index == 0:
                print('test-suite error: empty result on first test')
                sys.exit(1)
            else:
                test.result = tests[index-1].result

    return tests

def load_testsuite_folder(testsuite):
    # testsuite is a directory path

    current_dir = os.getcwd()
    os.chdir(testsuite)

    scripts = sorted([x for x in os.listdir('.') if x.endswith('.sed')])
    tests = list()
    for script in scripts:
        tests.append(FolderTest(script, testsuite))

    os.chdir(current_dir)

    return tests

def load_testsuite_batch(testsuite):
    # testsuite is a text file containing suite file names or folder names

    all_tests = list()
    with open(testsuite,'rt',**OPEN_ARGS) as f:
        for suite in [line.strip() for line in f]:
            all_tests.extend(load_testsuite(suite))
    return all_tests


# -- Running tests suite -----------------------------------------------------


def run_testsuite(tests, target, binary, exclude, elapsed_only):
    start = time.time()
    result = True
    debug = target is not None;
    n_succeeded = 0
    n_failed = 0
    n_ignored = 0
    for index, test in enumerate(tests):

        # numbers are printed starting from 1
        user_index = index + 1

        if test_requested(user_index, target):
            if test_ignored(test, exclude):
                test.ignore(user_index)
                n_ignored += 1
            else:
                if test.prepare():
                    test.run(binary,debug=debug)
                    if elapsed_only:
                        pass
                    else:
                        res = test.check(user_index, test.title)
                        if not res:
                            n_failed += 1
                        else:
                            n_succeeded += 1
                        result = result and res
                    test.postproc()
                else:
                    test.ignore(user_index)
                    n_ignored += 1

    end = time.time()
    elapsed = end - start

    if result:
        print('All tests ok (succeeded: %d, ignored: %d)' % (n_succeeded, n_ignored))
        print('Elapsed: %.3fs' % elapsed)
        sys.exit(0)
    else:
        print('Test failure (succeeded: %d, ignored: %d, failed: %d)' % (n_succeeded, n_ignored, n_failed))
        print('Elapsed: %.3fs' % elapsed)
        sys.exit(1)

def test_requested(index, target):
    if target is None:
        return True
    else:
        return index == target

def test_ignored(test, exclude):
    if test.title in exclude:
        return True
    else:
        return False


# -- Main --------------------------------------------------------------------


def parse_command_line():
    parser = argparse.ArgumentParser(usage=USAGE)

    parser.add_argument("-b", help="binary", action="store",
                        dest="binary", metavar='binary')
    parser.add_argument("-x", help="exclude file", action="store",
                        dest="exclude", metavar='test')
    parser.add_argument("-e", help=argparse.SUPPRESS, action="store_true",
                        dest="elapsed_only")
    parser.add_argument("file", help=argparse.SUPPRESS)
    parser.add_argument("target", nargs='?', help=argparse.SUPPRESS)

    return parser, parser.parse_args()

def main():
    _, args = parse_command_line()

    testsuite = args.file
    if args.target is not None:
        target = int(args.target)
    else:
        target = None

    try:
        # navigate to script directory
        current_dir = os.getcwd()
        test_dir = os.path.dirname(__file__)
        os.chdir(test_dir)

        if args.exclude:
            try:
                with open(args.exclude,'rt',**OPEN_ARGS) as f:
                    exclude = [line.strip() for line in f.readlines()]
            except:
                print('Error reading exclude file:', args.exclude)
                sys.exit(1)
        else:
            exclude = list()

        all_tests = load_testsuite(testsuite)
        run_testsuite(all_tests, target, args.binary, exclude, args.elapsed_only)

    finally:
        os.chdir(current_dir)

if __name__ == "__main__":
    main()
