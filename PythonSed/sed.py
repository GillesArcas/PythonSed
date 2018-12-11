#!/usr/bin/env python
from __future__ import print_function

BRIEF = """\
sed.py - python sed module and command line utility - sed.godrago.net\
"""

VERSION = '1.00'

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


import re
import sys
import os
import argparse
import string
import webbrowser


class Sed:
    """Usage:

    from sed import Sed, SedException
    sed = Sed()
    sed.no_autoprint = True/False
    sed.regexp_extended = True/False
    sed.load_script(myscript)
    sed.load_string(mystring)
    lines = sed.apply(myinputfile)                print lines to stdout
    lines = sed.apply(myinputfile, None)          do not print lines
    lines = sed.apply(myinputfile, myoutput.txt)  print lines to myoutput.txt
    """

    def __init__(self):
        self.PS = ''
        self.HS = ''
        self.first_cmd = None
        self.reader = Reader()
        self.output = None
        self.output_lines = []
        self.no_autoprint = False
        self.regexp_extended = False
        self.subst_successful = False
        self.append_buffer = []
        self.last_regexp = None
        self.commands = None

    def load_script(self, filename):
        try:
            if sys.version_info[0] == 2:
                with open(filename) as f:
                    string_list = f.readlines()
            else:
                with open(filename, encoding="latin-1") as f:
                    string_list = f.readlines()
        except:
            raise SedException('error reading ' + filename)
        self.load_string_list(string_list)

    def load_string(self, string):
        string_list = string.split('\n')
        self.load_string_list(string_list)

    def load_string_list(self, string_list):
        self.parse_flags(string_list)
        script = pack_script(string_list)
        self.commands = parse_script(script)
        self.first_cmd = self.commands[0]
        self.convert()
        self.create_write_files()

    def create_write_files(self):
        for command in self.commands:
            filename = None
            if command.function == 'w':
                filename = command.args
            elif command.function == 's':
                write = command.args[5]
                if write:
                    filename = command.args[6]
            if filename:
                try:
                    open(filename, 'w')
                except IOError:
                    raise SedException('unable to open %s' % filename)

    def parse_flags(self, script):
        # match #n on first line of script
        if script and script[0].startswith('#n'):
            self.no_autoprint = True

    def convert(self):
        for command in self.commands:
            command.convert(self.regexp_extended)

    def need_last_line(self):
        for command in self.commands:
            if (isinstance(command.address1, AddressDollar) or
                isinstance(command.address2, AddressDollar)):
                return True
        else:
            return False

    def dump_script(self):
        for command in self.commands:
            print(command)

    def readline(self):
        self.subst_successful = False
        return self.reader.readline()

    def islastline(self):
        return self.reader.islastline()

    def printline(self, line):
        self.output_lines.append(line)
        if self.output is not None:
            print(line, file=self.output)

    def flush_append_buffer(self):
        for line in self.append_buffer:
            self.printline(line)
        del self.append_buffer[:]

    def cache_regexp(self, reg_exp_container):
        # handle empty regexp with default to previous one
        if reg_exp_container is None:
            if self.last_regexp is None:
                raise SedException('empty regexp')
        else:
            self.last_regexp = reg_exp_container

        return self.last_regexp

    def apply(self, source_file, output=sys.stdout):
        self.reader.open(source_file, self.need_last_line())
        self.output = output
        self.output_lines = []
        self.PS = self.readline()

        while self.PS is not None:
            matched, command = False, self.first_cmd
            while command:
                prev_command = command
                matched, command = command.apply_func(self)

            # end of cycle

            if self.no_autoprint:
                pass
            elif prev_command.function == 'D':
                pass
            elif prev_command.function == 'd':
                if self.PS is None:
                    # if d triggered
                    pass
                else:
                    self.printline(self.PS)
            else:
                if self.PS is None:
                    # if n triggered at end of file
                    pass
                else:
                    self.printline(self.PS)

            self.flush_append_buffer()

            if prev_command.function == 'q' and matched:
                break

            if prev_command.function != 'D':
                self.PS = self.readline()

        return self.output_lines

    def match(self, address):
        return address.match(self)

    def write_subst_file(self, filename, line):
        with open(filename, 'at') as f:
            print(line, file=f)


class SedException(Exception):
    def __init__(self, message):
        self.message = 'sed.py error: %s' % message


class Reader:
    def __init__(self):
        self.input_file = None
        self.line = ''
        self.line_number = 0
        self.line_reader = None

    def open(self, source_file, need_last_line=False):
        try:
            if source_file == sys.stdin:
                self.input_file = sys.stdin
            else:
                if sys.version_info[0] == 2:
                    self.input_file = open(source_file)
                else:
                    self.input_file = open(source_file, encoding="latin-1")
        except IOError:
            raise SedException('unable to open %s' % source_file)
        except:
            raise

        self.line = ''
        self.line_number = 0
        self.line_reader = LineReader.factory(self.input_file, need_last_line)

    def getline(self):
        self.line = self.line_reader.readline()

    def islastline(self):
        return self.line_reader.islastline()

    def readline(self):
        self.getline()

        if self.line == '':
            return None
        else:
            self.line = self.line.rstrip('\r\n')
            self.line_number += 1
            return self.line


class LineReader:
    @staticmethod
    def factory(source, need_last_line):
        if not need_last_line:
            return LineReaderNoLast(source)
        else:
            return LineReaderBuffered(source)

class LineReaderNoLast:
    # used if last line address ($) not required

    def __init__(self, source):
        self.input_file = source

    def readline(self):
        return self.input_file.readline()

    def islastline(self):
        return False

class LineReaderBuffered:
    # used if last line address ($) required
    # buffer one line to be used from stdin

    def __init__(self, source):
        self.input_file = source
        self.nextline = self.input_file.readline()

    def readline(self):
        line = self.nextline
        if line != '':
            self.nextline = self.input_file.readline()
        return line

    def islastline(self):
        return self.nextline == ''


class AddressNumber:
    def __init__(self, number):
        self.number = number
    def __str__(self):
        return str(self.number)
    def match(self, sed):
        return self.number == sed.reader.line_number
    def convert(self, extended):
        pass

class AddressDollar:
    def __init__(self):
        pass
    def __str__(self):
        return '$'
    def match(self, sed):
        return sed.islastline()
    def convert(self, extended):
        pass

class AddressRegexp:
    def __init__(self, pattern, ignore_case):
        self.pattern = pattern
        self.ignore_case = ignore_case
        self.regexp = None

    def __str__(self):
        if self.ignore_case:
            return '%-8s|i' % self.pattern
        else:
            return self.pattern

    def convert(self, extended):
        self.regexp = Regexp.factory(self.pattern, extended, self.ignore_case)

    def match(self, sed):
        try:
            regexp = sed.cache_regexp(self.regexp)
            return regexp.search(sed.PS)

        except re.error as e:
            raise SedException('regexp: %s' % e.message)
        except:
            raise


class Command:
    num = 1

    def __init__(self, address1, address2, negate, function):

        if function == ':' and address1:
            raise SedException('wrong number of addresses')
        if function == '}' and address1:
            raise SedException('wrong number of addresses')
        if function == 'q' and address2:
            raise SedException('wrong number of addresses')

        self.num = Command.num
        Command.num += 1

        self.address1 = address1
        self.address2 = address2
        self.negate = negate
        self.function = function
        self.args = None
        self.next = None
        self.branch = None
        self.address_range_started = False

    @staticmethod
    def factory(address1, address2, negate, function):
        classes = { '{': Command_block,
                    '}': Command_block_end,
                    ':': Command_label,
                    'a': Command_a,
                    'b': Command_b,
                    'c': Command_c,
                    'd': Command_d,
                    'D': Command_D,
                    '=': Command_equal,
                    'g': Command_g,
                    'G': Command_G,
                    'h': Command_h,
                    'H': Command_H,
                    'i': Command_i,
                    'l': Command_l,
                    'n': Command_n,
                    'N': Command_N,
                    'p': Command_p,
                    'P': Command_P,
                    'q': Command_q,
                    'r': Command_r,
                    's': Command_s,
                    't': Command_t,
                    'w': Command_w,
                    'x': Command_x,
                    'y': Command_y,
                }
        if function in classes:
            return classes[function](address1, address2, negate, function)
        else:
            raise SedException('unknown function: %s' % function)

    def __str__(self):
        return '|%03d|%03d|%03d|%-10s|%-10s|%1s|%1s|%-20s|' % (self.num,
                                            self.next.num if self.next else 0,
                                            self.branch.num if self.branch else 0,
                                            self.address1, self.address2,
                                            '!' if self.negate else ' ',
                                            self.function,
                                            self.str_arguments())

    def allow_arguments(self):
        return self.function in ':btaicwrsy'

    def str_arguments(self):
        return self.args

    def parse_arguments(self, line, i):
        i, args = parse_arguments(line, i)
        self.args = args

        if self.args and not self.allow_arguments():
            raise SedException('arguments not allowed: %s %s' % (self.function, self.args))
        else:
            return i

    def convert(self, regexp_extended):
        if self.address1:
            self.address1.convert(regexp_extended)
        if self.address2:
            self.address2.convert(regexp_extended)

    def apply_func(self, sed):
        if self.address1 is None:
            matched = True
        elif self.address2 is None:
            matched = self.match_1addr(sed)
        else:
            matched = self.match_2addr(sed)

        if self.negate:
            matched = not matched

        if matched:
            return matched, self.apply(sed)
        else:
            return matched, self.next

    def match_1addr(self, sed):
        return sed.match(self.address1)

    def match_2addr(self, sed):
        if self.address_range_started:
            x = sed.match(self.address2)
            if x:
                self.address_range_started = False
            return True
        else:
            x = sed.match(self.address1)
            if x:
                self.address_range_started = True
            return x


class Command_block(Command):
    def parse_arguments(self, line, i):
        return i

    def apply(self, sed):
        # self.next is the first instruction after block
        # self.branch is the first instruction within block
        return self.branch

class Command_block_end(Command):
    def parse_arguments(self, line, i):
        return i

    def apply(self, sed):
        return self.next

class Command_label(Command):
    def apply(self, sed):
        return self.next

class Command_a(Command):
    def parse_arguments(self, line, i):
        i, self.args = parse_arguments_aic(line, i)
        return i

    def apply(self, sed):
        sed.append_buffer.append(self.args)
        return self.next

class Command_b(Command):
    def apply(self, sed):
        # if label missing, self.branch is None and will go to end of script
        return self.branch

class Command_c(Command):
    def parse_arguments(self, line, i):
        i, self.args = parse_arguments_aic(line, i)
        return i

    def apply(self, sed):
        if (not self.address2 or
            self.address2 and self.address_range_started == False):
            sed.printline(self.args)
        sed.PS = None
        return None

class Command_d(Command):
    def apply(self, sed):
        sed.PS = None
        return None

class Command_D(Command):
    def apply(self, sed):
        if '\n' in sed.PS:
            sed.PS = sed.PS[sed.PS.index('\n') + 1:]
        else:
            sed.PS = ''
            sed.PS = sed.readline()
        return None

class Command_equal(Command):
    def apply(self, sed):
        sed.printline('%d' % sed.reader.line_number)
        return self.next

class Command_g(Command):
    def apply(self, sed):
        sed.PS = sed.HS
        return self.next

class Command_G(Command):
    def apply(self, sed):
        sed.PS += '\n' + sed.HS
        return self.next

class Command_h(Command):
    def apply(self, sed):
        sed.HS = sed.PS
        return self.next

class Command_H(Command):
    def apply(self, sed):
        sed.HS += '\n' + sed.PS
        return self.next

class Command_i(Command):
    def parse_arguments(self, line, i):
        i, self.args = parse_arguments_aic(line, i)
        return i

    def apply(self, sed):
        sed.printline(self.args)
        return self.next

class Command_l(Command):
    def apply(self, sed):
        x = ''
        for c in sed.PS:
            if chr(32) <= c < chr(128) or c in '\n\t':
                x += c
            else:
                rep = oct(ord(c))
                rep = rep.replace('o', '') # remove 'o' from python 3
                rep = ('00' + rep)[-3:]    # pad on 3 characters
                x += '\\' + rep

        x += '$'
        x = x.replace('\n', r'\n')
        x = x.replace('\t', r'\t')
        width = 69
        for i in range(0, len(x), width):
            if i+width >= len(x):
                sed.printline(x[i:i+width])
            elif i+width == len(x) - 1 and x[i+width] == '$':
                sed.printline(x[i:i+width + 1])
                break
            else:
                sed.printline(x[i:i+width] + '\\')

        return self.next

class Command_n(Command):
    def apply(self, sed):
        if not sed.no_autoprint:
            sed.printline(sed.PS)
        sed.PS = sed.readline()
        if sed.PS is None:
            return None
        else:
            return self.next

class Command_N(Command):
    def apply(self, sed):
        newline = sed.readline()
        if newline is None:
            return None
        else:
            sed.PS = sed.PS + '\n' + newline
            return self.next

class Command_p(Command):
    def apply(self, sed):
        sed.printline(sed.PS)
        return self.next

class Command_P(Command):
    def apply(self, sed):
        if '\n' in sed.PS:
            sed.printline(sed.PS[:sed.PS.index('\n')])
        else:
            sed.printline(sed.PS)
        return self.next

class Command_q(Command):
    def apply(self, sed):
        # handled in sed.apply
        return None

class Command_r(Command):
    def apply(self, sed):
        # https://groups.yahoo.com/neo/groups/sed-users/conversations/topics/9096
        try:
            for line in open(self.args):
                line = line.replace('\n', '')
                sed.append_buffer.append(line)
        except:
            # "if filename cannot be read, it is treated as if it were an empty
            # file, without any error indication." (GNU sed manual page)
            pass

        return self.next

class Command_s(Command):
    def __init__(self, address1, address2, negate, function):
        Command.__init__(self, address1, address2, negate, function)
        self.xregexp = None

    def parse_arguments(self, line, i):
        i, self.args = parse_arguments_s(line, i)
        return i

    def convert(self, regexp_extended):
        Command.convert(self, regexp_extended)

        pattern, repl, _, _, ignore_case, _, _ = self.args

        self.regexp = Regexp.factory(pattern, regexp_extended, ignore_case)

        self.args[0] = '' if self.regexp is None else self.regexp.pattern
        self.args[1] = convert_replacement(repl)

    def str_arguments(self):
        pattern, repl, count, printit, ignore_case, write, filename = self.args

        # try to alight right delimiter by reducing repl width if necessary
        l0 = max(20, len(pattern)) + max(20, len(repl))
        if l0 <= 40:
            l = 20
        else:
            l = max(1, 20 - (l0 - 40))

        # count is 0 for g flag, flag removed if count = 1
        countflag = 'g' if count == 0 else count if count > 1 else ''

        flags = '%s%s%s%s' % (countflag,
                              'p' if printit else '',
                              'i' if ignore_case else '',
                              'w' if write else '')

        args = '%-20s|%-*s|%1s' % (pattern, l, repl, flags)

        if filename:
            args += ' ' + filename

        return args

    def apply(self, sed):
        _, repl, count, printit, _, write, filename = self.args

        # managing ampersand is done when converting to python format

        # manage empty regexp
        regexp = sed.cache_regexp(self.regexp)

        success, sed.PS = regexp.subn(repl, sed.PS, count=count)

        sed.subst_successful = sed.subst_successful or success

        if success:
            if printit:
                sed.printline(sed.PS)
            if write:
                sed.write_subst_file(filename, sed.PS)

        return self.next

class Command_t(Command):
    def apply(self, sed):
        # if label missing, self.branch is None and will go to end of script
        if sed.subst_successful:
            sed.subst_successful = False
            return self.branch
        else:
            return self.next

class Command_w(Command):
    def apply(self, sed):
        sed.write_subst_file(self.args, sed.PS)
        return self.next

class Command_x(Command):
    def apply(self, sed):
        sed.PS, sed.HS = sed.HS, sed.PS
        return self.next

class Command_y(Command):
    def __init__(self, address1, address2, negate, function):
        Command.__init__(self, address1, address2, negate, function)
        self.translate = None

    def parse_arguments(self, line, i):
        i, self.args = parse_arguments_y(line, i)
        return i

    def convert(self, regexp_extended):
        Command.convert(self, regexp_extended)
        self.args[0] = convert_argument_y(self.args[0])
        self.args[1] = convert_argument_y(self.args[1])
        try:
            try:
                # python2
                self.translate = string.maketrans(*self.args)
            except:
                # python3
                self.translate = str.maketrans(*self.args)
        except:
            raise SedException('y: incorrect arguments')

    def str_arguments(self):
        source_chars, dest_chars = self.args
        return '%-20s|%-20s' % (source_chars, dest_chars)

    def apply(self, sed):
        sed.PS = sed.PS.translate(self.translate)
        return self.next


class Regexp:
    # note that compile = False does not work for python 2.6 and below due to
    # re.subn lacking the flag parameter
    compile = True

    @staticmethod
    def factory(pattern, extended, ignore_case):
        if pattern == '':
            return None
        else:
            return Regexp(pattern, extended, ignore_case)

    def __init__(self, pattern, extended, ignore_case):
        self.pattern = convert_regexp(pattern, extended)
        self.ignore_case = ignore_case
        self.flags = re.DOTALL | (re.IGNORECASE if ignore_case else 0)
        if Regexp.compile:
            try:
                self.compiled = re.compile(self.pattern, self.flags)
            except re.error as e:
                raise SedException('regexp: %s' % e.message)
            except:
                raise
        else:
            self.compiled = None

    def search(self, string):
        if self.compiled:
            m = self.compiled.search(string)
        else:
            m = re.search(self.pattern, string, flags=self.flags)
        return m is not None

    def subn(self, repl, string, count):
        return re_sub_ex(self.pattern, self.compiled, repl, string, count, self.flags)


# -- Parser ------------------------------------------------------------------


def pack_script(script):
    # remove comments
    # comments following commands are removed during parsing
    script = [re.sub('^[ \t]*#.*', '', line) for line in script]

    # remove trailing spaces
    script = [line.rstrip() for line in script]

    # join lines ending with '\'
    packed = []
    for line in script:
        if packed and packed[-1].endswith('\\'):
            packed[-1] = packed[-1][:-1] + '\n' + line
        else:
            packed.append(line)

    # particular case of last line of script ending with slash
    if packed and packed[-1].endswith('\\'):
        packed[-1] = packed[-1][:-1] + '\n'

    return packed

def parse_script(script):
    try:
        commands = []
        for line in script:
            while len(line) > 0:
                i, command = parse_command(line)
                if command is None:
                    pass
                else:
                    commands.append(command)
                line = line[i:]

        link_commands(commands)
        return commands

    except SedException:
        raise
    except Exception as e:
        raise SedException('error parsing script: %s' % e)

def link_commands(commands):
    # link consecutive commands
    # resolve branchs
    # resolve blocks

    # link with next in script order. This is updated for blocks.
    for index, command in enumerate(commands[:-1]):
        command.next = commands[index + 1]

    # last command has no next
    commands[-1].next = None

    # one pass to make label dictionary
    target = dict()
    for command in commands:
        if command.function == ':':
            target[command.args] = command

    # one pass to resolve labels
    for command in commands:
        if command.function in 'bt':
            command.args = command.args.rstrip()
            if command.args == '':
                command.branch = None
            elif command.args in target:
                command.branch = target[command.args]
            else:
                raise SedException('undefined label: %s' % command.args)

    # one pass to remove extra line at start of aic commands
    for command in commands:
        if command.function in 'aic' and (command.args
                                     and command.args[0] == '\n'):
            command.args = command.args[1:]

    # one pass to resolve blocks
    block = []
    for command in commands:
        if command.function == '{':
            block.append(command)
        elif command.function == '}':
            opening = block.pop()
            opening.branch = opening.next
            opening.next = command.next
        else:
            pass


def parse_command(line):

    i, address1, address2, negate = parse_addresses(line, 0)
    i, function = parse_function(line, i)

    if function is None or function in '#;':
        # function is the first char after address. None if not found.
        if address1:
            raise SedException('unterminated command')
        else:
            return i, None

    command = Command.factory(address1, address2, negate, function)

    i = command.parse_arguments(line, i)

    return i, command

def ignore_space(s, i):
    m = re.match('([ \t]*)', s[i:])
    j = i + m.end(1)
    if j >= len(s):
        return j, None
    else:
        return j, s[j]

def parse_addresses(line, i):

    address1 = None
    address2 = None
    negate = False

    i, char = ignore_space(line, i)
    i, address1 = parse_address(line, i)

    i, char = ignore_space(line, i)
    if char == ',':
        if address1 is None:
            raise SedException('incorrect address range')

        i += 1
        i, char = ignore_space(line, i)
        i, address2 = parse_address(line, i)

        if address2 is None:
            raise SedException('incorrect address range')

    i, char = ignore_space(line, i)
    if char == '!':
        negate = True
        return i + 1, address1, address2, negate
    else:
        return i, address1, address2, negate

def parse_address(line, i):

    i, number = parse_number(line, i)
    if number:
        return i, AddressNumber(number)

    if i < len(line) and line[i] == '$':
        return i + 1, AddressDollar()

    if i < len(line) and line[i] == '\\':
        i, regexp = parse_regexp(line, i + 1)
    else:
        i, regexp = parse_regexp(line, i, '/')


    if regexp is None:
        return i, None
    else:
        if i < len(line) and line[i] == 'I':
            ignore_case = True
            i += 1
        else:
            ignore_case = False

        return i, AddressRegexp(regexp, ignore_case)

def parse_function(line, i):

    i, char = ignore_space(line, i)

    if i >= len(line):
        return len(line), None
    elif line[i] == '#':
        return len(line), line[i]
    else:
        return i + 1, line[i]

def parse_arguments(line, i):
    # aic, s and y have their own parsing functions
    # spaces after function are ignored
    i, char = ignore_space(line, i)
    i, tail = parse_tail_of_command(line, i)
    return i, tail

def parse_arguments_aic(line, i):
    i, char = ignore_space(line, i)

    # test for \ at start of argument enable to include leading spaces
    if i < len(line) and line[i] == '\\':
        i += 1

    # handle embedded \n
    arg = line[i:].replace(r'\n', '\n')

    return len(line), arg

def parse_arguments_s(line, i):
    i, left = parse_regexp(line, i)
    i, right = parse_replacement(line, i, delim=line[i - 1])

    i, tail = parse_tail_of_command(line, i)

    m = re.match('(([pgiI]|[0-9]+)*)(w (.*))?$', tail)
    if m is None:
        raise SedException('regexp: incorrect flags: %s' % tail)

    #g1, g3, g4 = m.group(1), m.group(3), m.group(4)
    flags, wcom, warg = m.group(1, 3, 4)

    printit = 'p' in flags
    ignore_case = 'i' in flags or 'I' in flags
    count = 0 if 'g' in flags else 1

    m = re.search('([0-9]+)', flags)
    if m:
        if 'g' in flags:
            raise SedException('regexp flags: g and number exclusive')
        else:
            count = int(m.group(1))

    if wcom is None:
        write = False
        filename = ''
    else:
        write = True
        filename = warg.strip()

    return i, [left, right, count, printit, ignore_case, write, filename]

def parse_arguments_y(line, i):
    if not line:
        raise SedException('y: unterminated command')

    sep = line[i]
    i += 1
    i, left = parse_argument_y(line, i, sep)
    i, right = parse_argument_y(line, i, sep)

    i, tail = parse_tail_of_command(line, i)
    if tail.strip():
        raise SedException('y: extra characters after command')

    return i, [left, right]

def parse_argument_y(line, i, sep):
    # enter with i on first character after separator
    # return first character after next separator

    j = i
    while j < len(line) and line[j] != sep:
        if line[j] == '\\':
            j += 2
        else:
            j += 1

    if j >= len(line):
        raise SedException('y: unterminated command')
    else:
        return j + 1, line[i:j]

def parse_tail_of_command(line, i):
    # return index of first char after tail plus tail string

    j = i
    while j < len(line) and line[j] not in ';}#':
        j += 1

    tail = line[i:j].rstrip()

    if j == len(line):
        return j, tail
    elif line[j] == '}':
        return j, tail
    elif line[j] == ';':
        return j + 1, tail
    elif line[j] == '#':
        return len(line), tail

def parse_number(line, i):
    m = re.match('([0-9]+)', line[i:])
    if m:
        return i + m.end(1), int(m.group(1))
    else:
        return i, None

def parse_regexp(s, i, delim=None):
    # find end of regexp starting at i in s
    # return position of first character after regexp delim

    if i >= len(s):
        return i, None

    if delim is None:
        delim = s[i]
        j = i + 1
    elif s[i] == delim:
        j = i + 1
    else:
        return i, None

    while j < len(s) and s[j] != delim:
        if s[j] == '\\':
            j += 2
        elif s[j] == '[':
            j = parse_charset(s, j) + 1
        else:
            j += 1

    if j < len(s):
        return j + 1, s[i + 1:j]
    else:
        return i, None

def parse_charset(s, i):
    # find end of charset starting at i in s
    # return position of closing bracket
    # handle []...] and [^]...]

    m = re.match('\[([^^]|\^.)[^]]*\]', s[i:])
    if m:
        return i + len(m.group(0)) - 1
    else:
        raise SedException('regexp: charset not closed')

def parse_replacement(s, i, delim):
    # find end of regexp right side starting at i in s
    # return position of first character after regexp

    if not s:
        return i, None

    j = i
    while j < len(s) and s[j] != delim:
        if s[j] == '\\':
            j += 2
        else:
            j += 1

    if j < len(s):
        return j + 1, s[i:j]
    else:
        raise SedException('subst: replacement incomplete')


# -- Conversion from sed syntax to python syntax -----------------------------


# Conversion of regexp

def convert_regexp(regexp, extended):
    if extended:
        return converted_regexp(regexp)
    else:
        return converted_regexp(reverse_slash(regexp))

def reverse_slash(regexp):
    r = ''
    i = 0
    while i < len(regexp):
        if regexp[i] in '(){}|+?':
            # slash
            r += '\\' + regexp[i]
            i += 1
        elif regexp[i] == '\\' and i + 1 < len(regexp):
            if regexp[i + 1] in '(){}|+?':
                # unslash
                r += regexp[i + 1]
                i += 2
            else:
                # keep all other slashed characters
                # (and avoid to start charset on \[)
                r += regexp[i:i + 2]
                i += 2
        elif regexp[i] == '[':
            j = parse_charset(regexp, i)
            r += regexp[i:j + 1]
            i = j + 1
        else:
            r += regexp[i]
            i += 1
    return r

def converted_regexp(regexp):
    # regexp must be an extended regexp

    r = ''
    i = 0
    while i < len(regexp):
        if regexp[i] == '\\':
            i, s = convert_slash(regexp, i)
            r += s
        elif regexp[i] == '[':
            i, s = convert_charset(regexp, i)
            r += s
        elif regexp[i] == '^' and i > 0 and regexp[i-1] not in '(|':
            r += r'\^'
            i += 1
        elif regexp[i] == '$' and i < len(regexp) - 1 and regexp[i+1] not in '|)':
            r += r'\$'
            i += 1
        elif regexp[i] == '$':
            # see http://www.regular-expressions.info/anchors.html#realend
            # without converting $ to \Z, re finds a end of line before end of
            # string and before a terminating \n :
            # re.sub('$', 'X', '\n') --> 'X\nX'
            r += r'\Z'
            i += 1
        elif regexp[i] in '+*?}':
            if i + 1 < len(regexp) and regexp[i + 1] in '+*?{':
                raise SedException('regexp: multiple quantifier ' + regexp)
            else:
                r += regexp[i]
                i += 1
        elif regexp[i:i + 2] == '(?':
                raise SedException('regexp: nothing to repeat ' + regexp)
        else:
            r += regexp[i]
            i += 1
    return r

def convert_slash(regexp, i):

    # slash in last position
    if i == len(regexp) - 1:
        raise SedException('regexp: illegal syntax')

    # keep sed special characters slashed
    elif regexp[i + 1] in r'\.^$*+?(){}[]|nt':
        return i + 2, regexp[i:i + 2]

    # backreferences
    elif regexp[i + 1].isdigit():
        return convert_backref(regexp, i)

    # extensions could take place here
    #elif regexp[i + 1] in 'sS':
    #    return i + 2, regexp[i:i + 2]

    # unslash all other characters
    else:
        return i + 2, regexp[i + 1]

def convert_backref(regexp, i):

    # avoid two digit backreferences
    if i + 2 < len(regexp) and regexp[i + 2].isdigit():
        return i + 3, regexp[i:i + 2] + '[%s]' % regexp[i + 2]

    # keep one digit backreferences
    else:
        return i + 2, regexp[i:i + 2]

def convert_charset(regexp, i):
    r = '['
    i += 1
    while i < len(regexp):
        if regexp[i] == ']':

            # closing bracket in first position
            if len(r) == 1:
                r += ']'
                i += 1

            # otherwise closing bracket is end of charset
            else:
                return i + 1, r + ']'

        elif regexp[i] == '\\':

            # \n and \t in charset
            if i + 1 < len(regexp) and regexp[i + 1] in 'nt':
                r += regexp[i:i + 2]
                i += 2

            # other slashes are doubled to avoid special meanings
            else:
                r += '\\\\'
                i += 1

        else:
            r += regexp[i]
            i += 1

# Conversion of replacement side

def convert_replacement(repl):
    # gnu extensions (\L, \U) are not handled
    r = ''
    i = 0
    while i < len(repl):
        if repl[i] == '\\' and i + 1 < len(repl) and repl[i + 1] in '0123456789':
            if i + 2 < len(repl) and repl[i + 2] in '0123456789':
                # force one digit backreference (\20)
                r += '\\g<' + repl[i + 1] + '>'
                i += 2
            else:
                r += repl[i:i + 2]
                i += 2
        elif repl[i] == '\\' and i + 1 < len(repl) and repl[i + 1] in '&':
            r += repl[i + 1]
            i += 2
        elif repl[i] == '\\' and i + 1 < len(repl) and repl[i + 1] in r'n\\':
            r += repl[i:i + 2]
            i += 2
        elif repl[i] == '\\':
            # ignore slash before any other character
            i += 1
        elif repl[i] == '&':
            r += '\\g<0>'
            i += 1
        else:
            r += repl[i]
            i += 1
    return r

# Conversion of y arguments

def convert_argument_y(s):
    r = ''
    i = 0
    while i < len(s):
        if s[i] == '\\':
            if i == len(s) - 1:
                raise SedException('y: not terminated argument')
            elif s[i + 1] == 'n':
                r += '\n'
                i += 2
            elif s[i + 1] == 't':
                r += '\t'
                i += 2
            else:
                r += s[i + 1]
                i += 2
        else:
            r += s[i]
            i += 1
    return r


# -- Extended substitution ---------------------------------------------------


def re_sub_ex(pattern, compiled, replacement, string, count, flags):
    # re.sub() extended:
    # - an unmatched group returns an empty string rather than None
    #   (http://gromgull.net/blog/2012/10/python-regex-unicode-and-brokenness/)
    # - the nth occurrence is replaced rather than the nth first ones
    #   (https://mail.python.org/pipermail/python-list/2008-December/475132.html)
    # - since 3.5, first agument of _expand must be a compiled regex

    class Match():
        def __init__(self, m):
            self.m = m
            self.string = m.string
        def group(self, n):
            return self.m.group(n) or ''
        def start(self, i):
            return self.m.start(i)
        def end(self, i):
            return self.m.end(i)

    class Nth(object):
        def __init__(self):
            self.calls = 0
            self.prevmatch = None
        def __call__(self, matchobj):
            if count == 0:
                match = Match(matchobj)
                try:
                    if self.prevmatch and match.group(0) == '' and match.start(0) == self.prevmatch.end(0):
                        return match.group(0)
                    else:
                        return re._expand(compiled, match, replacement)
                finally:
                    self.prevmatch = match
            else:
                self.calls += 1
                if self.calls == count:
                    return re._expand(compiled, Match(matchobj), replacement)
                else:
                    return matchobj.group(0)

    try:
        if compiled is None:
            string_res, nsubst = re.subn(pattern, Nth(), string, count, flags)
        else:
            string_res, nsubst = compiled.subn(Nth(), string, count)

    except re.error as e:
        raise SedException('regexp: %s' % e.message)
    except:
        raise

    # nsubst is the number of subst which would have been made without
    # the redefinition
    if count == 0:
        return (nsubst > 0), string_res
    else:
        return (nsubst >= count), string_res


# -- Main --------------------------------------------------------------------


def do_helphtml():
    if os.path.isfile('sed.html'):
        helpfile = 'sed.html'
    else:
        helpfile = r'http://sed.godrago.net/sed.html'

    webbrowser.open(helpfile, new=2)

USAGE = """
sed.py -h | -H | -v
       [-n][-r] -f <file> <text file>
       [-n][-r] -e <string> <text file>
"""

def parse_command_line():
    parser = argparse.ArgumentParser(usage=USAGE, add_help=False)

    parser.add_argument('-h', help='show this help message', action='store_true', dest='do_help')
    parser.add_argument('-H', help='open html help page', action='store_true', dest='do_helphtml')
    parser.add_argument("-v", help="version", action="store_true", dest="version")
    parser.add_argument("-f", help="script in file", action="store", dest="script_file", metavar='file')
    parser.add_argument("-e", help="script in string", action="store", dest="script_string", metavar='string')
    parser.add_argument("-n", help="print only if requested", action="store_true", dest="no_autoprint")
    parser.add_argument("-r", help="regexp extended", action="store_true", dest="regexp_extended")
    parser.add_argument("-d", help=argparse.SUPPRESS, action="store_true", dest="dump_script")
    parser.add_argument("target", nargs='?', help=argparse.SUPPRESS, default=sys.stdin)

    args = parser.parse_args()
    return parser, args

def main():
    parser, args = parse_command_line()

    try:
        sed = Sed()
        sed.no_autoprint = args.no_autoprint
        sed.regexp_extended = args.regexp_extended

        if args.version:
            print(BRIEF)
            print(VERSION)
            return
        elif args.do_help:
            parser.print_help()
            return
        elif args.do_helphtml:
            do_helphtml()
            return
        elif args.script_file:
            sed.load_script(args.script_file)
        elif args.script_string:
            sed.load_string(args.script_string)
        else:
            raise SedException('too few arguments')

        if args.dump_script:
            sed.dump_script()

        sed.apply(args.target)
        sys.exit(0)

    except SedException as e:
        print(e.message, file=sys.stderr)
        sys.exit(1)
    except:
        raise


if __name__ == "__main__":
    main()
