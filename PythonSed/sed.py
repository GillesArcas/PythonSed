#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

BRIEF = """
sed.py - python sed module and command line utility - sed.godrago.net\
"""

VERSION = '2.00'

COPYRIGHT = """
Copyright (c) 2021 Frank Schaeckermann (github dash fschaeckermann at snkmail dot com)'
Copyright (c) 2014 Gilles Arcas-Luque (gilles dot arcas at gmail dot com)
"""

DESCRIPTION = """\
This module implements a GNU sed version 4.8 compatible sed command and module.

This version is a major overhaul by Frank Schaeckermann of the original code done
by Gilles Arcas-Luque.

All missing sed command line options (based on GNU sed version 4.8) where added,
together with some further enhancements:

- restructured the code to be object-oriented through and through
- allows for multiple input files and multiple script-parts (-e and -f)
- inplace editing
- added all the documented backslash-escapes
- allow for much more powerful Python-syntax in regexp (-p or --python-syntax)
- added very detailed error handling with appropriate messages pointing at the
  exact script source location of the error
- supports \\L \\U \\l \\u and \\E in the replacement string for case modifications

Things not working like in GNU sed version 4.8 are
- no support for character classes like [:lower:] due to missing support for them
  in Pyhton regular expressions (anybody having a list of all lower case unicode
  characters?)
- the e command is not implemented

These are the only two tests of the test suites contained in the project, that
fail. All other tests pass - including using newline as a delimiter for the s
command.

"""

LICENSE = """\
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

from tempfile import NamedTemporaryFile

import traceback
import re
import sys
import os
import ast
import argparse
import string
import webbrowser

if sys.version_info[0]==2:
    PY2 = True
else:
    PY2 = False 
    from io import open as open

class ScriptLine (object):
    debug = 0
    
    def __init__(self, line=None,
                       lineno=0,
                       scriptIdx=0,
                       sourceIdx=0,
                       source=None):

        if line is not None:
            self.line = line
            while self.line.endswith('\n'):
                self.line = self.line[0:-1]
            if self.line.endswith('\\'):
                self.is_continued = True
                self.line = self.line[0:-1] # remove continuation character
            else:
                self.is_continued = False
            self.line += '\n' # and add back the escaped new line character
            self.pos = 0
            self.next = None
            
            if type(source)==int:
                l = '-e #{}'.format(source)
            elif source is None:
                l = 'stream #{}'.format(sourceIdx)
            else:
                l = '-f {}'.format(source)
            self.source = l+' line {}'.format(lineno)

            self.scriptIdx = scriptIdx
            
            self.last_char = ' '
            self.last_pos = -1
            self.last_source = self.source
            
    def __str__(self):
        return self.line

    def __repr__(self):
        return self.position+': '+self.line
        
    @property
    def position(self):
        return self.last_source+' char '+str(self.last_pos+1)
        
    def copy(self):
        new = ScriptLine() # create empty object to be filled directly
        new.line = self.line
        new.is_continued = self.is_continued
        new.pos = self.pos
        new.next = self.next
        new.source = self.source
        new.scriptIdx = self.scriptIdx
        new.last_char = self.last_char
        new.last_pos = self.last_pos
        new.last_source = self.last_source
        return new
        
    def become(self,scriptLine):
        self.line = scriptLine.line
        self.is_continued = scriptLine.is_continued
        self.pos = scriptLine.pos
        self.next = scriptLine.next
        self.source = scriptLine.source
        self.scriptIdx = scriptLine.scriptIdx
        # we do not override last_char, last_pos nor last_source!
        
    def add_next(self,scriptLine):
        if (not self.is_continued
            and scriptLine.is_empty()):
            return self
        else:
            self.next = scriptLine
            return scriptLine
        
    def is_empty(self):
        chk = self.line.strip()
        return len(chk)==0 or chk.startswith('#')
        
    def get_char(self):
        if self.debug>=3:
            print('get_char entering',file=sys.stderr)
        self.last_source = self.source
        self.last_pos = self.pos
        if self.pos<len(self.line):
            char = self.line[self.pos]
            self.pos += 1
            self.last_char = char
            if self.pos==len(self.line) and self.is_continued:
                self.become(self.next)
            if self.debug>=3:
                print('get_char returning "{}"'.format(char),file=sys.stderr)
            return char
        self.last_char = '\0'
        if self.debug>=3:
            print('get_char returning \\0',file=sys.stderr)
        return '\0'
    
    def continue_on_next_line(self):
        if self.pos==len(self.line) and self.next:
            self.become(self.next)
        
    def look_ahead(self):
        if self.pos<len(self.line):
            return self.line[self.pos]
        return '\0'

    def get_non_space_char_within_current_line(self):
        char = self.get_char()
        while char!='\n' and char.isspace():
            char = self.get_char()
        return char
        
    def get_non_space_char_within_continued_lines(self):
        char = self.get_char()
        while char.isspace():
            char = self.get_char()
        return char
        
    def skip_space_within_continued_lines(self):
        char = self.last_char
        while char.isspace():
            char = self.get_char()
        return char
    
    def skip_over_end_of_cmd(self):
        char = self.last_char
        if char=='\0' or char.isspace():
            char = self.get_non_space_char_within_continued_lines()
        while (char=='\0' or char=='#' or char==';'):
            if char=='\0':
                if self.next is not None:
                    self.become(self.next)
                else:
                    return char
            elif char=='#':
                while self.is_continued:
                    self.become(self.next)
                self.pos = len(self.line) # skip to end of line
            char = self.get_non_space_char_within_continued_lines()
        return char
        
    def is_end_of_cmd(self):
        char = self.last_char
        if char.isspace():
            char = self.get_non_space_char_within_continued_lines() # :todo:
        return char in ';#}\0' # block-end is implicit eoc


PLACE_NOESCAPE = 0
PLACE_TEXT = 1
PLACE_REPL = 2
PLACE_REGEXP = 4
PLACE_CHRSET = 8
PLACE_NAMES = {
        PLACE_TEXT: 'normal text',
        PLACE_REPL: 'replacement',
        PLACE_REGEXP: 'regular expression',
        PLACE_CHRSET: 'character set',
    }

class Script(object):
    
    def __init__(self,sed):
        # we need this for access to configuration
        self.sed = sed
        self.needs_last_line = False
        
        self.first_line = None
        self.last_line = None
        self.script_line = None
        self.obj_idx = 0
        self.strg_idx = 0
        self.file_idx = 0
        self.script_idx = 0
        self.referenced_labels = {}
        self.defined_labels = {}
        self.started_blocks = []
        self.first_command_entry = None
        self.sed_compatible = sed.sed_compatible

    def __str__(self):
        if self.first_command_entry is None:
            return '<nothing compiled yet>'
        result = ''
        command = self.first_command_entry
        while command:
            result += str(command)+'\n'
            if command.function=='{':
                command = command.branch
            else:
                command = command.next
        return result
    
    # convenience methods that are
    # all delegated to script_line
    @property
    def position(self):
        return self.script_line.position
         
    def get_char(self):
        return self.script_line.get_char()
        
    def get_non_space_char_within_current_line(self):
        return self.script_line.get_non_space_char_within_current_line()
        
    def get_non_space_char_within_continued_lines(self):
        return self.script_line.get_non_space_char_within_continued_lines()
        
    def skip_over_end_of_cmd(self):
        return self.script_line.skip_over_end_of_cmd()

    def skip_space_within_continued_lines(self):
        return self.script_line.skip_space_within_continued_lines()
    
    def continue_on_next_line(self):
        self.script_line.continue_on_next_line()
        
    def is_cmd_end(self):
        return self.script_line.is_end_of_cmd()
    
    def look_ahead(self):
        return self.script_line.look_ahead()
        
    # methods to add script content
        
    def add_string(self, strg):
        self.script_idx += 1
        self.strg_idx += 1
        lineno = 0
        for line in strg.split('\n'):
            lineno += 1
            self._add(ScriptLine(
                          line,
                          lineno,
                          self.script_idx,
                          self.strg_idx,
                          self.strg_idx))
        # no continuation check here, since the
        # commands a,i and c can span multiple
        # strings
        
        
    def add_file(self, filename, encoding):
        self.script_idx += 1
        self.file_idx += 1
        lineno = 0
        try:
            args = {} if PY2 else { 'encoding': encoding }
            with open(filename, 'rt', **args) as f:
                for line in f.readlines():
                    lineno += 1
                    self._add(ScriptLine(
                                    line,
                                    lineno,
                                    self.script_idx,
                                    self.file_idx,
                                    filename))
        except Exception as e:
            raise SedException('','Error reading script file {file}: {err}', file=filename, err=str(e))
        # if last line is continued, add another empty line to resolve continuation
        if self.last_line.is_continued:
            self._add(ScriptLine('\n',lineno+1,self.script_idx,self.obj_idx,None))
        
                            
    def add_object(self, script_stream):
        self.script_idx += 1
        self.obj_idx += 1
        lineno = 0
        for line in script_stream.readlines():
            lineno += 1
            self._add(ScriptLine(
                            line,
                            lineno,
                            self.script_idx,
                            self.obj_idx,
                            None))
        # if last line is continued, add another empty line to resolve continuation
        if self.last_line.is_continued:
            self._add(ScriptLine('\n',lineno+1,self.script_idx,self.obj_idx,None))
        
        
    def _add(self,script_line):
        self.first_command_entry = None
        if self.last_line:
            self.last_line = self.last_line.add_next(script_line)
        else:
            self.first_line = script_line
            self.last_line = script_line
            

    def _check_continuation(self):
        if self.last_line.is_continued:
            raise SedException(self.last_line.source,'Invalid line continuation on last script line.')


    def get_first_command(self):
        if self.first_command_entry is None:
            self.compile()
        return self.first_command_entry
        
    
    # methods to parse and compile the script
    def compile(self):
        if not self.first_line:
            raise SedException('','No script specified.')
        
        self._check_continuation() # in case the last -e ended in line continuation!
        
        ScriptLine.debug = self.sed.debug
        
        self.referenced_labels = {}
        self.defined_labels = {}
        self.started_blocks = []
        self.parse_flags()
        
        self.first_command_entry = None
        last_command = None
        self.script_line = self.first_line.copy()

        command = self.get_command()
        while command is not None:
            if not last_command:
                self.first_command_entry = command
            else:
                last_command.next = command
            last_command = command
            command = self.get_command()
            
        if len(self.started_blocks)>0:
            raise SedException('','Unclosed blocks starting at {blockpos}',
                               blockpos=', '.join(b.position for b in self.started_blocks))
            
        if len(self.referenced_labels)>0:
            raise SedException('','Undefined labels referenced: {lbls}',
            lbls='\n    '+'\n    '.join('{} at {}'.format(ref.label,ref.position)
                                         for ref_list in self.referenced_labels.values()
                                         for ref in ref_list))
                    
        
    def parse_flags(self):
        # get flags from first line of script
        if self.first_line.line:
            flags=(self.first_line.line.strip()+"   ")[0:3].strip()
            if flags in ['#n','#nr','#rn']:
                self.sed.no_autoprint = True
            if flags in ['#r','#nr','#rn']:
                self.sed.regexp_extended = True

            
    def get_command(self):
        position, addr_range, function = self.get_address()
        # function is the first char after address range. '' if not found and None at script end
        while function=='':
            if addr_range:
                raise SedException(position,'Address without a command')
            position, addr_range = self.get_address()
        if function is None:
            return None
        else:
            return Command.factory(self,addr_range,function)


    def get_char_list(self,delim):
        """ this parses a list of characters for the y command """
        strg = ''
        pystrg = ''
        unescstrg = ''
        char = self.get_char()
        pychr = ''
        while char!='\0' and char!=delim:
            if char=='\\':
                if self.look_ahead()==delim:
                    char = self.get_char()
                    pychr = char
                    unesc = char
                else:
                    char,pychr,unesc = self.get_escape(PLACE_TEXT)
                    if unesc is None:
                        unesc = pychr
            else:
                pychr = char
                unesc = pychr
            strg += char
            pystrg += pychr
            unescstrg += unesc
            char = self.get_char()
        return char,strg,pystrg,unescstrg


    def get_name(self, kind, alpha_only=True, skip_space=False):
        nme = ''
        if skip_space:
            char = self.get_non_space_char_within_continued_lines() # :todo:
        else:
            char = self.get_char()
        while char not in '\0;#}' and (char.isalpha() or not (char.isspace() or alpha_only)):
            if char=='\\':
                SedException(self.position,'No backslash escapes allowed in {kind} name.', kind=kind)
            nme += char
            char = self.get_char()
        return char,nme
    

    def unescape_char(self,strg):
        """ is only called with strings that have
            already been checked for invalid escapes
            and only in textual context - no regexp
        """
        return ast.literal_eval(strg)


    def get_number(self,first_digit=None):
        if first_digit is None:
            char = self.get_char()
        else:
            char = first_digit
        if char not in '0123456789':
            raise SedException(self.position,'Expected number')
        num = 0
        while char in '0123456789':
            num = num*10+int(char)
            char = self.get_char()
        return char,num
    
    
    def get_to_line_end(self):
        result = ''
        char = self.get_non_space_char_within_current_line()
        if char=='\n':
            # there was no non-space character on the current line
            # but it has a continuation on the next line.
            char = self.get_char()
        while char!='\0':
            if char=='\\':
                _,_,unesc = self.get_escape(PLACE_TEXT)
                char = unesc
            result += char
            char = self.get_char()
        if result.endswith('\n'):
            result = result[:-1] # remove possibly trailing new line
        return result
    
    def get_escape(self,place):
        """
        places: 1 normal text
                2 replacement
                4 regexp
                8 charset
        sed: 12: \\s \\S \\w \\W
              4: \\b \\B \\< \\> \\<backtic> \\<forwardtic>
              2: \\E \\U \\u \\L \\l
              6: \\1..\\9
             15: \\a \\f \\n \\r \\t \\v \\
             15: \\cx \\d### \\o### \\x##
        py:  12: \\w \\W \\s \\S \\d \\D
              4: \\b \\B \\A \\Z
              6: \\1..\\9 \\10..\\99
             15: \\a \\f \\n \\r \\t \\v \\
             15: \\0 \\01..\\07 \\001..\\377 \\x##
             15: \\u#### \\U######## \\N{name}
             
         returns (original string, python string, unescaped character - or None for functional escapes)
        """
        pos = self.position
        if self.sed_compatible and place==PLACE_CHRSET:
            if (self.look_ahead() not in 'afnrtvsSwW'
                 +('cdox' if self.sed_compatible else '0123xdDuUN')):
                return '\\','\\\\','\\'

        char = self.get_char()
        # first the stuff that is the same for both
        if char=='a':
            return '\\a','\\a','\a'
        elif char=='f':
            return '\\f','\\f','\f'
        elif char=='n':
            return '\\n','\\n','\n'
        elif char=='r':
            return '\\r','\\r','\r'
        elif char=='t':
            return '\\t','\\t','\t'
        elif char=='v':
            return '\\v','\\v','\v'
        elif char=='\\':
                return '\\\\','\\\\','\\'
        elif (place&(PLACE_REGEXP+PLACE_CHRSET)
                and char in 'sSwW'
              or place&PLACE_REGEXP and char in 'bB'):
            char = '\\'+char
            return char,char,None
        elif place==PLACE_REPL and char in 'lLuUE':
            # \\u and \\U collides with Python unicode
            # escapes, but for replacement strings
            # modifying case is more important
            return '\\'+char,'\\'+char,None

        if self.sed_compatible:
            if char=='0':
                return '\\0','\\0','\0'
            if place==PLACE_REGEXP:
                if char==u"\u0060":
                    return u'\\\u0060',r'\A',None
                elif char==u"\u00B4":
                    return u'\\\u00B4',r'\Z',None
                elif char=='<':
                    return r'\<',r'(?:\b(?=\w))',None
                elif char=='>':
                    return r'\>',r'(?:\b(?=\W))',None
            if place&(PLACE_REGEXP+PLACE_REPL):
                if char.isdigit():
                    return '\\'+char,'(?:\\'+char+')', None
            if char=='c':
                char = self.get_char()
                if char=='\\':
                    raise SedException(self.script_line.position,'Recursive escaping after \\c not allowed')
                if char.islower():
                    char_ord = ord(char.upper())^64
                else:
                    char_ord = ord(char)^64
                char = r'\c'+char
                return char,self.hex_escape(char, pos,str(char_ord),10),chr(char_ord)
            elif char=='d':
                dec_num = (self.get_char()
                       +self.get_char()
                       +self.get_char())
                char = r'\d'+dec_num
                return char,self.hex_escape(char, pos,dec_num,10),chr(int(dec_num))
            elif char=='o':
                oct_num = (self.get_char()
                          +self.get_char()
                          +self.get_char())
                char = r'\o'+oct_num
                return char,self.hex_escape(char, pos,oct_num,8),chr(int(oct_num,8))
            elif char=='x':
                hex_num = (self.get_char()
                       +self.get_char())
                char = r'\x'+hex_num
                return char,self.hex_escape(char, pos,hex_num,16),chr(int(hex_num,16))
        else:
            if (char in 'AZ' and place==PLACE_REGEXP or char in 'dD' and place&(PLACE_REGEXP+PLACE_CHRSET)):
                char = '\\'+char
                return char,char,None
            if char.isdigit():
                dig1 = int(char)
                dig2 = self.look_ahead()
                if dig2.isdigit():
                    char += dig2
                    dig2 = int(self.get_char())
                    dig3 = self.look_ahead()
                    if dig3.isdigit() and int(dig3)<8:
                        char += dig3
                        dig3 = int(self.get_char())
                        if dig1>3 or dig2>7:
                            raise SedException(pos,'\\{esc} is not a valid octal escape.',esc=char)
                        return '\\'+char, '\\'+char, chr(int(char,8))
                    elif dig1==0:
                        if dig2>7:
                            raise SedException(pos,'\\{esc} is not a valid octal escape.',esc=char)
                        return '\\'+char, '\\'+char, chr(int(char,8))
                    else:
                        # we got a two digit decimal escape - a back reference
                        if place!=PLACE_REGEXP and place!=PLACE_REPL:
                            raise SedException(pos,'\\{esc} is a group backreference outside of a regexp or replacement.', esc=char)
                        char = '\\'+char
                        return char, char, None
                elif dig1=='0':
                    return '\\0','\\0','\0'
                elif (place!=PLACE_REGEXP
                        and place!=PLACE_REPL):
                    raise SedException(pos,'\\{esc} is a group backreference outside of a regexp or replacement.', esc=char)
                else:
                    # we got a one digit back reference
                    char = '\\'+char
                    return char,char,None
                
            if char=='x':
                hex_num = (self.get_char()
                       +self.get_char())
                char = '\\x'+hex_num
                return char,self.hex_escape(char, pos,hex_num,16),chr(int(hex_num,16))
            elif char=='u':
                hex_num = (self.get_char()
                          +self.get_char()
                          +self.get_char()
                          +self.get_char())
                char = '\\u'+hex_num
                try:
                    _ = int(hex_num,16)
                    return char, char, self.unescape_char(char)
                except:
                    raise SedException(pos,'Invalid hex code in unicode escape {esc}',esc=char)
            elif char=='U':
                hex_num = (self.get_char()
                          +self.get_char()
                          +self.get_char()
                          +self.get_char()
                          +self.get_char()
                          +self.get_char()
                          +self.get_char()
                          +self.get_char())
                char = '\\U'+hex_num
                try:
                    _ = int(hex_num,16)
                    return char,char,self.unescape_char(char)
                except:
                    raise SedException(pos,'Invalid hex code in unicode escape {esc}',esc=char)
            elif char=='N':
                char = self.get_char()
                if char!='{':
                    raise SedException(pos,'Invalid unicode escape \\N{char}. Expected { but found {char}',char=char)
                char,nme = self.get_name('unicode character')
                if char!='}':
                    raise SedException(pos,'Invalid unicode escape \\N{{{esc}. Missing } behind the character name.',esc=nme)
                nme += '\\N{'+nme+'}'
                return nme,nme,self.unescape_char(nme)
            
        if char.isalnum() and place!=PLACE_TEXT:
            raise SedException(pos,'\\{char} is not a valid escape in a {plce}.', char=char, plce=PLACE_NAMES[place])
        # keep everything else as it was
        return '\\'+char,'\\'+char,char
                
    def get_regexp(self, delim, address=True):
        position = self.position
        swap_escapes = not self.sed.regexp_extended
        
        char = self.get_char()
        if char==delim:
            regexp = SedRegexpEmpty(position,delim,address=address)
        else:
            # we use this to keep track of $ characters
            # in the python pattern since we may need to
            # modify them to achieve sed compatibility,
            # because the dollar sign has context-dependent
            # behavior in sed:
            #  1. $ not at the end of a regular expression
            #     are to be taken literally
            #  2. in a single line substitution $ only
            #     matches the end of the pattern space
            #  3. in a multi line substitution $ matches
            #     the end of the pattern space AND right
            #     before any new-line
            # This is a problem, because in a python regexp
            # $ always behaves like 3.
            # So for 1. we need to replace $ with \\$ and
            # for 2. we need to replace $ with \\Z.
            # Unfortunately, we can only decide what to do
            # for 2. AFTER we parsed the flags behind
            # the regexp and in the case of the s command
            # even later - after parsing the sed-flags 
            dollars = []
            
            pattern = ''
            py_pattern = ''
            pychr = ''
            last_char = ''
            last_pychr = ''
            while char!='\0' and char!=delim:
                pychr = char
                if char=='\\':
                    if swap_escapes and self.look_ahead() in '(){}|+?':
                        chr2 = self.get_char()
                        char += chr2
                        pychr = chr2
                    elif self.look_ahead()==delim:
                        char = self.get_char()
                        pychr = char
                    else:
                        char,pychr,_ = self.get_escape(PLACE_REGEXP)
                elif char in '(){}|+?':
                    if swap_escapes:
                        pychr = '\\'+pychr
                elif char=='[':
                    char,pychr = self.get_charset()
                elif self.sed_compatible:
                    # in sed a ^ not at the beginning of
                    # a regexp must be taken literally
                    if char=='^' and not (last_pychr in ['(','|','']):
                        pychr = '\\^'
                    elif char=='$':
                        # remember this dollar sign's position in py_pattern
                        dollars.append(len(py_pattern))
                        
                if self.sed_compatible and pychr=='?' and last_pychr in ['(','+','*']:
                    raise SedException(self.position,'Invalid regexp: {last}{char} is not allowed in sed compatible mode.', char=char, last=last_char)
                
                pattern += char
                py_pattern += pychr
                last_char = char
                last_pychr = pychr

                char = self.get_char()
        
            if char!=delim:
                raise SedException(self.position,'Invalid regex: expected closing delimiter {delim}',delim=delim)
            
            regexp = SedRegexp(position,delim,pattern,py_pattern,dollars,address=address)

        if address:
            multi_line = False
            ignore_case = False
            char = self.get_non_space_char_within_continued_lines()
            while char in ['I','M']:
                if char=='M':
                    if multi_line:
                        raise SedException(self.position,'Invalid regex: flag M specified multiple times')
                    regexp.set_multi_line()
                    multi_line = True
                elif char=='I':
                    if ignore_case:
                        raise SedException(self.position,'Invalid regex: flag I specified multiple times')
                    regexp.set_ignore_case()
                    ignore_case = True
                char = self.get_non_space_char_within_continued_lines()
            
        return char, regexp
    
    def hex_escape(self,esc,pos,val,base):
        try:
            i = int(val,base)
            return (r'\x'+format(i,'02x'))
        except:
            raise SedException(pos,'{esc} is an invalid escape. Error when converting digits of base {base}.',esc=esc,base=base)
                
    def get_charset(self):
        # handle []...] and [^]...]
        charset = '['
        char = self.get_char()
        if char=='^':
            charset += char
            char = self.get_char()
        if char==']':
            charset += char
            char = self.get_char()
        pyset = charset
        while char!=']' and char!='\0':
            if char=='[' and self.look_ahead() in ':=.':
                position = self.position
                class_char = self.get_char()
                class_name = { ':': 'character class',
                               '=': 'equivalence class',
                               '.': 'collating symbol' }[class_char]
                
                char2,nme = self.get_name(class_name)
                char = self.look_ahead()
                if char2!=class_char or char!=']':
                    raise SedException(position,'[{clschr}{nme}{char2}{char} in charset is not a proper {cls} specification',
                                       clschr=class_char,
                                       nme=nme,
                                       char2=char2,
                                       char=char,
                                       cls=class_name)
                char = self.get_char()
                class_spec = '['+class_char+nme+class_char+']'
                charset += class_spec
                pyset += charset
                raise SedException(position,'The {nme} specification {spec} is not supported by Python regular expressions.',
                                   nme=class_name,
                                   spec=class_spec)
            elif char=='\\':
                esc,pyesc,_ = self.get_escape(PLACE_CHRSET)
                charset += esc
                pyset += pyesc
            else:
                charset += char
                pyset += char
            char = self.get_char()
            
        if char!=']':
            raise SedException(self.position,'Invalid regex: charset not closed')
        return charset+char, pyset+char
        
    def get_replacement(self, delim):
        replacement = Replacement()
        char = self.get_char()
        while char!='\0' and char!=delim:
            if char=='\\':
                if self.look_ahead()==delim:
                    char = self.get_char()
                    replacement.add_literal('\\'+char,char)
                else:
                    char,pychr,unesc = self.get_escape(PLACE_REPL)
                    if unesc is not None:
                        replacement.add_literal(char,unesc)
                    else:
                        replacement.add_escape(char,pychr)
            elif char=='&' and self.sed.sed_compatible:
                replacement.add_group(char,0)
            else:
                replacement.add_literal(char,char)
            char = self.get_char()
        return replacement
        
    def get_address(self):
        from_addr = None
        addr_range = None
        
        char = self.script_line.skip_over_end_of_cmd() # :todo:
        position = self.position
        if char=='\0':
            return position, None, None
            
        if char=='\\' or char=='/':
            if char=='\\':
                char = self.get_char()
            char,regexp = self.get_regexp(char,address=True)
            # make sure we keep sed compatibility
            regexp.process_flags_and_dollars()
            from_addr = AddressRegexp(self.sed, regexp)
        elif char in '0123456789':
            char,num = self.get_number(char)
            if char=='~':
                char,step = self.get_number()
                if step>0:
                    from_addr = AddressStep(self.sed, num, step)
                elif num==0:
                    from_addr = AddressZero(self.sed)
                else:
                    from_addr = AddressNum(self.sed, num)
            elif num==0:
                from_addr = AddressZero(self.sed)
            else:
                from_addr = AddressNum(self.sed, num)
        elif char=='$':
            from_addr = AddressLast(self.sed)
            char = self.get_char()
            self.needs_last_line = True
        else: # no address found
            return position, AddressRangeNone(), char

        char = self.script_line.skip_space_within_continued_lines() # :todo:
        if char==',':
            char = self.script_line.get_non_space_char_within_continued_lines() # :todo:
            
            if char=='\0':
                raise SedException(self.position,'Invalid address specification: missing to-address')
            
            exclude = False
            excl_pos = self.position
            if char=='-':
                exclude = True
                char = self.get_non_space_char_within_continued_lines() # :todo:
                
            if char=='\\' or char=='/':
                if char=='\\':
                    char = self.get_char()
                char,regexp = self.get_regexp(char,address=True)
                # make sure we keep sed compatibility
                regexp.process_flags_and_dollars()
                if isinstance(from_addr,AddressZero):
                    addr_range = AddressRangeZeroToRegexp(from_addr, regexp, exclude)
                else:
                    addr_range = AddressRangeToRegexp(from_addr, regexp, exclude)
            elif char in '0123456789':
                num_pos = self.position
                char,num = self.get_number(char)
                if num==0:
                    raise SedException(num_pos,'Invalid use of zero address')
                addr_range = AddressRangeToNum(from_addr, num, exclude)
            elif char=='~':
                char,multiple = self.get_number()
                if multiple==0:
                    if exclude:
                        raise SedException(excl_pos,'Invalid use of exclude flag')
                    addr_range = AddressRangeFake(from_addr)
                else:
                    addr_range = AddressRangeToMultiple(from_addr, multiple, exclude)
            elif char=='+':
                char,count = self.get_number()
                if count==0:
                    if exclude:
                        raise SedException(excl_pos,'Invalid use of exclude flag')
                    addr_range = AddressRangeFake(from_addr)
                else:
                    addr_range = AddressRangeToCount(from_addr, count, exclude)
            elif char=='$':
                addr_range = AddressRangeToLastLine(from_addr, exclude)
                char = self.get_char()
                self.needs_last_line = True
            else:
                SedException(self.position,'Invalid to-address in address range')
                
        else: # only an address found - no range
            addr_range = AddressRangeFake(from_addr)
        char = self.script_line.skip_space_within_continued_lines() # :todo:
            
        if (isinstance(from_addr,AddressZero) and
            not isinstance(addr_range,
                           AddressRangeZeroToRegexp)):
            raise SedException(position,'Invalid use of zero address')
                
        if char=='!':
            char = self.get_non_space_char_within_continued_lines() # :todo:
            addr_range.set_negate(True)
                
        return position,addr_range,char

    def reference_to_label(self,label_ref_command):
        label = label_ref_command.label
        if label in self.defined_labels:
            label_ref_command.branch = self.defined_labels[label]
        else:
            ref = self.referenced_labels.get(label,None)
            if ref:
                ref.append(label_ref_command)
            else:
                self.referenced_labels[label] = [ label_ref_command ]
            
    def define_label(self,label_def_command):
        label = label_def_command.label
        if label in self.defined_labels:
            raise SedException(self.position,'Label {lbl} redefined at {redef} (first appeared at {orig})',
                               lbl=label, redef=label_def_command.position, orig=self.defined_labels[label].position)
        self.defined_labels[label] = label_def_command
        
        references = self.referenced_labels.pop(label,[])
        for cmd in references:
            cmd.branch = label_def_command
            
    def register_block_start(self,block_start_cmd):
        self.started_blocks.append(block_start_cmd)
        
    def process_block_end(self,block_end_cmd):
        if len(self.started_blocks)>0:
            block_start_cmd = self.started_blocks.pop()
            if block_start_cmd.next:
                block_start_cmd.branch = block_start_cmd.next
            else: # we have got an empty block!
                block_start_cmd.branch = block_end_cmd
            block_start_cmd.next = block_end_cmd
        else:
            raise SedException(block_end_cmd.position,'No matching open block for block end command')
            
                

class Sed(object):
    """Usage:

    from PythonSed import Sed, SedException
    sed = Sed()
    sed.no_autoprint = True/False
    sed.regexp_extended = True/False
    sed.in_place = None/Backup-Suffix
    sed.separate = True/False
    sed.debug = debug level (0=no debug, 1=debug execution, 2=debug compile, 3=trace compile)
    sed.load_script(myscript)
    sed.load_string(mystring)
    sed.load_scripts(myscripts)               list of file names or literal scripts (prefixed with \n to distinguish from file names)
    lines = sed.apply(myinput)                print lines to stdout
    lines = sed.apply(myinput, None)          do not print lines
    lines = sed.apply(myinput, myoutput)      print lines to myoutput

    myinput and myoutput may be:
    * strings, in that case they are interpreted as file names
    * file-like objects (including streams)

    Note that if myinput or myoutput are file-like objects, they must be closed
    by the caller.
    """

    def __init__(self,
                 encoding='latin-1',
                 line_length=70,
                 no_autoprint=False,
                 regexp_extended=False,
                 sed_compatible=True,
                 in_place=None,
                 separate=False,
                 debug=0):
    
        self.encoding = encoding
        self.line_length = line_length
        self.no_autoprint = no_autoprint
        self.regexp_extended = regexp_extended
        self.sed_compatible = sed_compatible
        self.in_place = in_place
        self.separate = separate
        self.debug = debug
        
        self.writer = None
        self.reader = None
        
        self.PS = ''
        self.HS = ''
        self.subst_successful = False
        self.append_buffer = []
        self.script = Script(self)
        
        self.exit_code = 0
        
    @staticmethod
    def normalize_string(strng,line_length):
        if strng is None:
            yield ''
            return 
        
        x = ''
        for c in strng:
            if 32 <= ord(c) <= 127:
                if c=='\\':
                    x += c
                x += c
            elif c=='\n':
                x += '\\n'
            elif c=='\t':
                x += '\\t'
            else:
                x += '\\'+('00'+oct(ord(c))[1:])[-3:]
                
        width = line_length-1
        while len(x)>width:
            yield (x[:width]+'\\')
            x = x[width:]
        yield (x+'$')
        
    def write_state(self,title):
        self.stateWriter.write(title)
        
    def load_script(self,
                    filename,
                    encoding=None):
        if encoding is None:
            encoding = self.encoding
        if type(filename)==str:
            self.script.add_file(filename,encoding)
        else:
            self.script.add_object(filename)

    def load_string(self, string):
        self.script.add_string(string)
        
    def load_string_list(self,string_list):
        for string in string_list:
            self.script.add_string(string)

    def readline(self):
        self.subst_successful = False
        return self.reader.readline()

    def is_last_line(self):
        return self.reader.is_last_line()
    
    def file_line_no(self):
        return self.reader.line_number
    
    def printline(self, source, line):
        self.writer.printline(line)
        if self.debug>0:
            if not line.endswith('\n'):
                line += '\n'
            prefix = 'printing ('+source+'): '
            for lne in line.split('\n')[:-1]:
                print(prefix+lne,file=sys.stderr) 
            
    def flush_append_buffer(self):
        for line in self.append_buffer:
            self.printline('appnd',line)
        self.append_buffer = []

    def getReader(self,
                  source_files,
                  encoding,
                  writer,
                  separate,
                  needs_last_line):
        if needs_last_line:
            if writer.is_inplace():
                return ReaderBufSepInplace(source_files, encoding, writer)
            elif separate:
                return ReaderBufSep(source_files, encoding)
            else:
                return ReaderBufOne(source_files, encoding)
        elif writer.is_inplace():
            return ReaderUnbufSepInplace(source_files, encoding, writer)
        elif separate:
            return ReaderUnbufSep(source_files, encoding)
        else:
            return ReaderUnbufOne(source_files, encoding)
        
    def apply(self, source_files, output=sys.stdout):
                
        self.writer = Writer(output,
                             self.encoding,
                             self.in_place,
                             self.debug)

        first_cmd = self.script.get_first_command()
        if first_cmd is None:
            raise SedException('','Empty script specified.')
        
        if self.debug>0:
            print(str(self.script),file=sys.stderr)
            self.stateWriter = StateWriter(self)
            
        self.reader = self.getReader(
                        source_files,
                        self.encoding,
                        self.writer,
                        self.separate,
                        self.script.needs_last_line)
        
        self.exit_code = 0

        self.HS = ''
        self.subst_successful = False
        self.append_buffer = []
        SedRegexp.last_regexp = None
        
        try:
            self.PS = self.readline()
            while self.PS is not None:
                matched, command = False, first_cmd
                if self.debug>0:
                    print('############### new cycle'.ljust(self.line_length,'#'),file=sys.stderr)
                    print('Auto Print: {}'.format('Off' if self.no_autoprint else 'On'),file=sys.stderr)
                    print('Input File: {}[{}]'.format(self.reader.source_file_name,self.reader.line_number),file=sys.stderr)
                    print('Output To : {}'.format(self.writer.current_filename),file=sys.stderr)
                    self.write_state('current')
                while command:
                    prev_command = command
                    matched, command = command.apply_func(self)
    
                if self.debug>0:
                    print('############### cycle end '.ljust(self.line_length,'#'),file=sys.stderr)
                    print('Auto Print: {}'.format('Off' if self.no_autoprint else 'On'),file=sys.stderr)
                    print('Input File: {}[{}]'.format(self.reader.source_file_name,self.reader.line_number),file=sys.stderr)
                    print('Output To : {}'.format(self.writer.current_filename),file=sys.stderr)
    
                if not (self.no_autoprint
                        or prev_command.function in 'DQ'
                        or self.PS is None):
                    self.printline('autop',self.PS)
                
                self.flush_append_buffer()
    
                if prev_command.function in 'qQ' and matched:
                    self.exit_code = prev_command.exit_code or 0
                    break
    
                if prev_command.function != 'D':
                    self.PS = self.readline()
        except:
            traceback.print_exception(*sys.exc_info(),file=sys.stderr)
            self.exit_code = 1
        finally:
            self.reader.close()
            return self.writer.finish()

class StateWriter(object):
    def __init__(self,sed):
        self.sed = sed
        self.last_PS = []
        self.last_HS = []
        self.last_append_buffer = []
        self.last_subst_successful = None

    def _create_printable(self,lines_list,width):
        result = []
        for lines in lines_list:
            splitted = list(lne+'\n' for lne in lines.split('\n'))
            if lines.endswith('\n'):
                splitted = splitted[0:-1] # remove trailing empty line from end of list
            else:
                splitted[-1] = splitted[-1][:-1] # remove newline from last line
                
            for line in splitted:
                for normalized in self.sed.normalize_string(line,width):
                    result.append('|{lne:<{width}s}|'.format(lne=normalized,width=width))
        if len(result)==0:
            result.append('|{lne:<{width}s}|'.format(lne='',width=width))
        return result
    
    def _write_list(self,title,last_list,new_list):
        print(title+':',file=sys.stderr)
        for i in range(len(new_list)):
            flag = '  '
            if i>=len(last_list) or last_list[i]!=new_list[i]:
                flag = '* '
            print(flag+new_list[i],file=sys.stderr)
    
    def write(self,title):
        width = self.sed.line_length-4        
        print(('--------------- '+title+' ').ljust(self.sed.line_length,'-'),file=sys.stderr)

        if self.sed.PS is not None:
            new = list(lne+'\n' for lne in self.sed.PS.split('\n'))
            new[-1] = new[-1][0:-1] # remove newline from last line since PS never ends with \n
        else:
            new = []
        new = self._create_printable(new,width)
        self._write_list('Pattern Space',self.last_PS,new)
        self.last_PS = new
        
        new = list(lne+'\n' for lne in self.sed.HS.split('\n'))
        new[-1] = new[-1][0:-1] # remove newline from last line since PS never ends with \n
        new = self._create_printable(new,width)
        self._write_list('Hold Space',self.last_HS,new)
        self.last_HS = new
        
        new = self._create_printable(self.sed.append_buffer, width)
        self._write_list('Append Buffer',self.last_append_buffer,new)
        self.last_append_buffer = new
        
        new = '' if self.last_subst_successful==self.sed.subst_successful else '*'
        print('{}Substitution successful: {}'.format(new,self.sed.subst_successful),file=sys.stderr)
        self.last_subst_successful = self.sed.subst_successful
            
class Writer (object):
    def __init__(self,output,encoding,in_place,debug=0):
        self.encoding = encoding
        self.in_place = in_place
        self.debug = debug
        
        self.output_lines = []
        self.open_files = {}
        self.current_filename = None
        self.current_output = None
        self.current_output_opened = False
        self.inplace_filenames = {}

        if in_place is None:
            if type(output)==str:
                self.current_filename = output
                try:
                    args = {} if PY2 else { 'encoding': self.encoding }
                    self.current_output = open(output, 'wt', **args)
                    self.current_output_opened = True
                except Exception as e:
                    raise SedException('',"Can not open output file {file}: {err}",file=output,err=str(e))
            elif output is not None:
                self.current_output = output
                
    def is_inplace(self):
        return self.in_place is not None
                    
    def printline(self, line):
        line += '\n'
        if self.current_output:
            self.current_output.write(line)
        self.output_lines.append(line)
            
    def add_write_file(self,filename):
        if self.open_files.get(filename) is None:
            args = {} if PY2 else { 'encoding':self.encoding }
            self.open_files[filename] = open(filename, 'wt', **args)
        
    def write_to_file(self,filename,line):
        open_file = self.open_files.get(filename)
        if open_file is None:
            if filename=='/dev/stdout' or filename=='-':
                open_file = sys.stdout
            elif filename=='/dev/stderr':
                open_file = sys.stderr
            else:
                raise SedException('','File {file} not opened for writing.',file=filename)
        if not line.endswith('\n'):
            line += '\n'
        if self.debug>0:
            print('writing to '+filename+': '+line,end='',file=sys.stderr)
        open_file.write(line)
        
    def open_inplace(self,file_name):
        self.current_filename = os.path.abspath(file_name)
        directory = os.path.dirname(self.current_filename)
        self.current_output = NamedTemporaryFile(dir=directory, mode='wt', delete=False)
        self.current_output_opened = True
        
    def close_inplace(self):
        if self.current_output:
            self.current_output.close()
            self.current_output_opened = False
            if len(self.in_place)==0:
                bkup = NamedTemporaryFile(
                         dir=os.path.dirname(self.current_filename),
                         prefix=os.path.basename(self.current_filename)+'.',
                         delete=False)
                bkup.close()
                bkup = bkup.name
            elif '*' in self.in_place:
                bkup = self.in_place.replace('*', os.path.basename(self.current_filename))
                if not '/' in bkup:
                    bkup = os.path.join(os.path.dirname(self.current_filename),bkup)
            else:
                bkup = self.current_filename +self.in_place
            os.rename(self.current_filename,bkup)
            os.rename(self.current_output.name, self.current_filename)
            if self.in_place=='':
                os.remove(bkup)
            
    def finish(self):
        if self.current_output_opened:
            if self.in_place is not None:
                try:
                    self.close_inplace()
                except:
                    pass
            else:
                try:
                    self.current_output.close()
                except:
                    pass
        for open_file in self.open_files.values():
            try:
                open_file.close()
            except:
                pass
        return self.output_lines
            
     
class ReaderUnbufOne(object):
    def __init__(self, source_files, encoding):
        if type(source_files)==list:
            if (len(source_files)==0 or
                len(source_files)==1
                  and source_files[0] is None):
                self.source_files = [sys.stdin]
            else:
                self.source_files = source_files
        elif source_files is None:
            self.source_files = [sys.stdin]
        else:
            self.source_files = [source_files]
            
        self.encoding = encoding
        
        self.line = ''
        self.line_number = 0
        self.source_file_name = None
        self.open_next()
        
        self.open_files = {}
        
    def open_next(self):
        if len(self.source_files)==0:
            self.input_stream = None
            self.input_stream_opened = False
            return

        source_file = self.source_files.pop(0)
            
        if type(source_file) != str:
            self.input_stream = source_file
            self.source_file_name = '<stream>'
            self.input_stream_opened = False
        elif source_file=='-':
            self.input_stream = sys.stdin
            self.source_file_name = '<stdin>'
            self.input_stream_opened = False
        else:
            try:
                args = {} if PY2 else { 'encoding': self.encoding }
                self.input_stream = open(source_file, mode='rt', **args)
                self.source_file_name = source_file
                self.input_stream_opened = True
            except IOError as e:
                raise SedException('','Unable to open input file {file}: {err}',file=source_file, err=str(e))
            except:
                raise

    def readline(self):
        if self.input_stream is None:
            return None

        self.line = self.next_line()

        while self.line=='':
            if self.input_stream_opened:
                self.input_stream.close()
            self.open_next()
            if self.input_stream is None:
                return None
            self.line = self.next_line()
            
        self.line_number += 1    
        if self.line.endswith('\n'):
            self.line = self.line[:-1]
            
        return self.line
            
    def is_last_line(self):
        return False

    def next_line(self):
        return self.input_stream.readline()
        
    def readline_from_file(self,filename):
        if filename in self.open_files:
            open_file = self.open_files.get(filename)
            if open_file is not None:
                line = open_file.readline()
                if len(line)==0:
                    open_file.close()
                    self.open_files[filename] = None
                    return ''
                return line
            else:
                return ''
        elif filename=='/dev/stdin' or filename=='-':
            return sys.stdin.readline()
        else:
            open_file = None
            try:
                args = {} if PY2 else { 'encoding': self.encoding }
                open_file = open(filename,mode='rt',**args)
                self.open_files[filename] = open_file
                return open_file.readline()
            except:
                if open_file:
                    open_file.close()
                self.open_files[filename] = None
                return ''
            
    def close(self):
        if self.input_stream_opened:
            try:
                self.input_stream.close()
            except:
                pass
        for open_file in self.open_files.values():
            if open_file:
                try:
                    open_file.close()
                except:
                    pass
        
        
class ReaderUnbufSep(ReaderUnbufOne):
    def open_next(self):
        self.line_number = 0
        super(ReaderUnbufSep,self).open_next()
        

class ReaderUnbufSepInplace(ReaderUnbufSep):
    def __init__(self, source_files,encoding,writer):
        files = source_files
        if type(source_files)!=list:
            files = [ source_files ]
        if len(files)==0:
            raise SedException('','Can not use stdin as input for inplace-editing.')
        for open_file in files:
            if open_file is None or open_file=='-':
                raise SedException('','Can not use stdin as input for inplace-editing.')
            elif type(open_file)!=str:
                raise SedException('','Can not use streams or files as input for inplace-editing.')

        self.writer = writer
        super(ReaderUnbufSepInplace,self).__init__(source_files,encoding)
        
    def open_next(self):
        self.writer.close_inplace()
        super(ReaderUnbufSepInplace,self).open_next()
        if self.input_stream is not None:
            self.writer.open_inplace(
                self.source_file_name)
        return self.input_stream
        

class ReaderBufOne(ReaderUnbufOne):
    # used if last line address ($) required
    # buffer one line to be used from input stream
    def open_next(self):
        super(ReaderBufOne,self).open_next()
        if self.input_stream:
            self.nextline = self.input_stream.readline()
        
    def next_line(self):
        if self.nextline != '':
            line = self.nextline
            self.nextline = self.input_stream.readline()
            return line
        else:
            return ''

    def is_last_line(self):
        return self.nextline=='' and len(self.source_files)==0
        
        
class ReaderBufSep(ReaderBufOne):
    def open_next(self):
        self.line_number = 0
        super(ReaderBufSep,self).open_next()
        
    def is_last_line(self):
        return self.nextline==''
        

class ReaderBufSepInplace(ReaderBufSep):
    def __init__(self, source_files,encoding,writer):
        files = source_files
        if type(source_files)!=list:
            files = [ source_files ]
        if len(files)==0:
            raise SedException('','Can not use stdin as input for inplace-editing.')
        for filename in files:
            if filename is None or filename=='-':
                raise SedException('','Can not use stdin as input for inplace-editing.')
            elif type(filename)!=str:
                raise SedException('','Can not use streams or files as input for inplace-editing.')
        self.writer = writer
        super(ReaderBufSepInplace,self). __init__(source_files,encoding)
        
    def open_next(self):
        self.writer.close_inplace()
        super(ReaderBufSepInplace,self).open_next()
        if self.input_stream is not None:
            self.writer.open_inplace(
                self.source_file_name)
        return self.input_stream


class Command(object):
    num = 1
    def __init__(self, script, addr_range, function):
        self.position = script.position
        self.num = Command.num
        Command.num += 1
        
        if (function in [':','}'] and not isinstance(addr_range,AddressRangeNone)):
            raise SedException(self.position,'No address can be specified for command {cmd}',cmd=function)
        elif (function=='q'
               and not (isinstance(addr_range,AddressRangeFake)
                        or isinstance(addr_range,AddressRangeNone))):
            raise SedException(self.position,'No address range can be specified for command {cmd}',cmd=function)

        self.function = function
        self.addr_range = addr_range
        self.next = None
        self.branch = None
        self.parse_arguments(script)

    @staticmethod
    def factory(script, addr_range, function):
        if function in COMMANDS:
            return COMMANDS[function](script, addr_range, function)
        else:
            raise SedException(script.position,'Unknown command {cmd}',cmd=function)

    def __str__(self):
        return self.toString(20)

    def toString(self,addr_width=''):
        return '|{num:03d}|{nxt:3s}|{brnch:3s}| {addr:<{width}s} {cmd:1s}{args}'.format(
            num=self.num,
            nxt=(('%03d'%self.next.num)
                  if self.next
                  else ' - '),
            brnch=(('%03d'%self.branch.num)
                  if self.branch
                  else '   '),
            addr=str(self.addr_range),
            width=addr_width,
            cmd=self.function,
            args=self.str_arguments())

    def str_arguments(self):
        return ''

    def parse_arguments(self, script):
        _ = script.get_char()
        if not script.is_cmd_end():
            raise SedException(self.position,'Extra characters after command {cmd}', cmd=self.function)

    def apply_func(self, sed):
        if self.addr_range.is_active():
            if sed.debug>0:
                print('=============== executing '.ljust(sed.line_length,'='),file=sys.stderr)
                print(self.toString(),file=sys.stderr)
                cmd = self.apply(sed)
                sed.write_state('after')
                return True,cmd
            else:
                return True, self.apply(sed)
        elif sed.debug>0:
            print('=============== skipping '.ljust(sed.line_length,'='),file=sys.stderr)
            print(self.toString(),file=sys.stderr)
            sed.write_state('current')
        return False, self.next


class Command_block(Command):
    def __init__(self, script, addr_range, function):
        super(Command_block,self).__init__(script, addr_range, function)
        script.register_block_start(self)
        
    def apply(self, sed):  # @UnusedVariable
        # self.next is the first instruction after block
        # self.branch is the first instruction within block
        return self.branch
    
    def parse_arguments(self, script):
        _ = script.get_non_space_char_within_continued_lines() # :todo:
        # do not check for command end, since it is implicit


class Command_block_end(Command):
    def __init__(self, script, addr_range, function):
        super(Command_block_end,self).__init__(script, addr_range, function)
        script.process_block_end(self)
        
    def apply(self, sed):  # @UnusedVariable
        return self.next


class _Command_with_label(Command):
    def parse_arguments(self,script):
        _, self.label = script.get_name('label',alpha_only=False,skip_space=True)
        if not script.is_cmd_end():
            raise SedException(self.position,'Command {cmd} can not have any arguments after label', cmd=self.function)
    
    def str_arguments(self):
        return ' '+self.label
            
class Command_label(_Command_with_label):
    def __init__(self, script, addr_range, function):
        super(Command_label,self).__init__(script, addr_range, function)
        if self.label is None or len(self.label)==0:
            raise SedException(self.position,'Missing label for command :')
        script.define_label(self)
        
    def apply(self, sed):  # @UnusedVariable
        return self.next
            
class Command_a(Command):
    def parse_arguments(self, script):
        self.text = script.get_to_line_end()

    def apply(self, sed):
        sed.append_buffer.append(self.text)
        return self.next
    
    def str_arguments(self):
        return ' '+self.text

class Command_A(Command_a):
    def apply(self, sed):
        sed.PS += self.text
        return self.next
        
class Command_b(_Command_with_label):
    def __init__(self, script, addr_range, function):
        super(Command_b,self).__init__(script, addr_range, function)
        if self.label:
            script.reference_to_label(self)
        
    def apply(self, sed):  # @UnusedVariable
        # if label was omitted, self.branch is None and will go to end of script
        if self.branch:
            return self.branch.next
        else:
            return None
        
class Command_c(Command_a):
    def apply(self, sed):
        if self.addr_range.first_line:
            sed.printline('cmd c',self.text)
        sed.PS = None
        return None

class Command_C(Command_a):
    def apply(self, sed):
        if self.addr_range.first_line:
            sed.PS = self.text
            return self.next
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
        sed.printline('cmd =',str(sed.reader.line_number))
        return self.next
    
class Command_F(Command):
    def apply(self,sed):
        sed.printline('cmd F',sed.reader.source_file_name)
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

class Command_i(Command_a):
    def apply(self, sed):
        sed.printline('cmd i',self.text)
        return self.next

class Command_I(Command_a):
    def apply(self, sed):
        sed.PS = self.text+sed.PS
        return self.next
        
class Command_l(Command):
    def parse_arguments(self,script):
        char = script.get_non_space_char_within_continued_lines()
        if char.isdigit():
            _,self.line_length = script.get_number(char)
        else:
            self.line_length = None
        if not script.is_cmd_end():
            raise SedException(script.position,'Only an integer number can follow command l as parameter')
            
    def apply(self, sed):
        if self.line_length:
            line_length = self.line_length
        else:
            line_length = sed.line_length
        for lne in Sed.normalize_string(sed.PS, line_length):
            sed.printline('cmd l',lne)
        return self.next
    
    def str_arguments(self):
        return ' '+str(self.line_length) if self.line_length else ''

class Command_n(Command):
    def apply(self, sed):
        if not sed.no_autoprint:
            sed.printline('cmd n',sed.PS)
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
        sed.printline('cmd p',sed.PS)
        return self.next

class Command_P(Command):
    def apply(self, sed):
        try:
            n = sed.PS.index('\n')
            sed.printline('cmd P',sed.PS[:n])
        except ValueError:
            sed.printline('cmd P',sed.PS)
        return self.next

class Command_q(Command):
    def parse_arguments(self,script):
        char = script.get_non_space_char_within_continued_lines()
        if char.isdigit():
            _,self.exit_code = script.get_number(char)
        else:
            self.exit_code = None
        if not script.is_cmd_end():
            raise SedException(script.position,
                               'Only an integer number can follow command {cmd} as parameter'
                                 .format(self.function))

    def apply(self, sed):  # @UnusedVariable
        # handled in sed.apply
        return None
    
    def str_arguments(self):
        return ' '+str(self.exit_code)

class Command_Q(Command_q):
    def apply(self, sed):  # @UnusedVariable
        # handled in sed.apply
        return None
    
class Command_r(Command):
    def parse_arguments(self,script):
        self.filename = script.get_to_line_end()
        if not self.filename:
            raise SedException(self.position,'Missing file name for command {cmd}', cmd=self.function)
        
    def apply(self, sed):
        # https://groups.yahoo.com/neo/groups/sed-users/conversations/topics/9096
        try:
            args = {} if PY2 else { 'encoding': sed.encoding }
            with open(self.filename, 'rt', **args) as f:
                for line in f:
                    sed.append_buffer.append(line[:-1] if line.endswith('\n') else line)
        except:
            # "if filename cannot be read, it is treated as if it were an empty
            # file, without any error indication." (GNU sed manual page)
            pass
        return self.next
    
    def str_arguments(self):
        return ' '+self.filename

class Command_R(Command_r):
    def apply(self, sed):
        line = sed.reader.readline_from_file(self.filename)
        if line:
            sed.append_buffer.append(line[:-1] if line.endswith('\n') else line)
        return self.next

class Command_s(Command):
    def parse_arguments(self,script):
        self.count = None
        self.printit = False
        self.ignore_case = False
        self.multiline = False
        self.globally = False
        self.filename = None
        self.delim = script.get_char()
        
        if self.delim=='\n':
            script.continue_on_next_line()
        
        char, self.regexp = script.get_regexp(self.delim,address=False)
        if char!=self.delim:
            raise SedException(script.position,'Missing delimiter ({delim}) after regexp parameter in command s', delim=self.delim)
            
        if self.delim=='\n':
            script.continue_on_next_line()

        self.repl = script.get_replacement(self.delim)
        if self.repl is None:
            raise SedException(script.position,'Missing delimiter ({delim}) after replacement parameter in command s', delim=self.delim)
                        
        char = script.get_non_space_char_within_continued_lines() # :todo:
        while char not in ';#}\0':
            if char=='w':
                self.filename = script.get_to_line_end()
                char = '\0'
                if not self.filename:
                    raise SedException(script.position,'Missing file name for command s option w')
                try:
                    script.sed.writer.add_write_file(self.filename)
                except IOError as e:
                    raise SedException(script.position,'Unable to open file {file} for output from command s with option w: {err}',
                        file=self.filename,
                        err=str(e))
            elif char=='p':
                if self.printit:
                    raise SedException(script.position,'Flag p specified twice for command s')
                self.printit = True
                char = script.get_non_space_char_within_continued_lines() # :todo:
            elif char=='i' or char=='I':
                if self.ignore_case:
                    raise SedException(script.position,'Flag i specified twice for command s')
                self.ignore_case = True
                self.regexp.set_ignore_case()
                char = script.get_non_space_char_within_continued_lines() # :todo:
            elif char=='m' or char=='M':
                if self.multiline:
                    raise SedException(script.position,'Flag m specified twice for command s')
                self.multiline = True
                self.regexp.set_multi_line()
                char = script.get_non_space_char_within_continued_lines() # :todo:
            elif char=='g':
                if self.globally:
                    raise SedException(script.position,'Flag g specified twice for command s')
                self.globally = True
                char = script.get_non_space_char_within_continued_lines() # :todo:
            elif char in '0123456789':
                if self.count:
                    raise SedException(script.position,'Count specified twice for command s')
                self.count = 0
                while char in '0123456789':
                    self.count *= 10
                    self.count += int(char)
                    char = script.get_char()
                char = script.skip_space_within_continued_lines() # :todo:
            else:
                raise SedException(script.position,'Invalid flag {flag} for command s',flag=char)
        if self.count is None:
            self.count = 1
        # make sure we keep sed compatibility
        self.regexp.process_flags_and_dollars()
            
    def str_arguments(self):        
        flags = 'g' if self.globally else ''
        if self.count and self.count>1:
            flags += str(self.count)
        if self.printit:
            flags += 'p'
        if self.ignore_case:
            flags += 'i'
        if self.multiline:
            flags += 'm'
        if self.filename:
            flags += 'w '+self.filename

        return "{regex}{repl}{delim}{flags}".format(
            delim=self.delim,
            regex=self.regexp.toString(),
            repl=self.repl.string,
            flags=flags)

    def apply(self, sed):
        # pattern, repl, count, printit, inplace, write, filename = self.args

        # managing ampersand is done when converting to python format

        success, sed.PS = self.regexp.subn(self.repl, sed.PS, self.globally, self.count, sed.sed_compatible)

        sed.subst_successful = sed.subst_successful or success

        if success:
            if self.printit:
                sed.printline('cmd s',sed.PS)
            if self.filename:
                sed.writer.write_to_file(self.filename, sed.PS)

        return self.next

class Command_t(Command_b):
    def apply(self, sed):
        # if label was omitted, self.branch is None and will go to end of script
        if sed.subst_successful:
            sed.subst_successful = False
            if self.branch:
                return self.branch.next
            else:
                return None
        else:
            return self.next

class Command_T(Command_b):
    def apply(self, sed):
        # if label was omitted, self.branch is None and will go to end of script
        if sed.subst_successful:
            sed.subst_successful = False
            return self.next
        elif self.branch:
            return self.branch.next
        else:
            return None

class Command_v(Command):
    def apply(self, sed): # @UnusedVariable
        pass
        return self.next
    
    def parse_arguments(self, script):
        _,self.version = script.get_name('version',alpha_only=False,skip_space=True)
        if not self.version:
            self.version = '4.0'
        match = re.match(r'^([0-9]+)(?:\.([0-9]+)(?:\.([0-9]+))?)?$',self.version)
        if match:
            version  = "%03d" % (int(match.group(1)))
            release  = "%03d" % (int(match.group(2)) if match.group(2) else 0)
            fixlevel = "%03d" % (int(match.group(3)) if match.group(3) else 0)
            if version+release+fixlevel>'004008000':
                raise SedException(self.position,'Requested version {version} is above provided version 4.8.0'.format(version=self.version))
        else:
            raise SedException(self.position,'Invalid version specification {version}. Use a number like 4.8.0'.format(version=self.version))
    
    def str_arguments(self):
        return ' '+self.version
    
class Command_w(Command_r):
    def apply(self, sed):
        sed.writer.write_to_file(self.filename, sed.PS)
        return self.next
    
    def parse_arguments(self, script):
        super(Command_w,self).parse_arguments(script)
        try:
            script.sed.writer.add_write_file(self.filename)
        except IOError as e:
            raise SedException(self.position,'Unable to open file {file} for output for command {cmd}: {err}',
                file=self.filename,
                cmd=self.function,
                err=str(e))

class Command_W(Command_w):
    def apply(self, sed):
        sed.writer.write_to_file(self.filename,sed.PS.split('\n',1)[0])
        return self.next
        
class Command_x(Command):
    def apply(self, sed):
        sed.PS, sed.HS = sed.HS, sed.PS
        return self.next

class Command_y(Command):
    def __init__(self, script, addr_range, function):
        super(Command_y,self).__init__(script, addr_range, function)

    def parse_arguments(self, script):
        self.delim = script.get_char()
        
        if self.delim=='\n':
            script.continue_on_next_line()
            
        char, _, _, self.left = script.get_char_list(self.delim)
        if char!=self.delim:
            raise SedException(script.position,'Missing delimiter {delim} for left parameter to command y', delim=self.delim)
        if not self.left:
            raise SedException(self.position,'Missing left parameter to command y')
            
        if self.delim=='\n':
            script.continue_on_next_line()

        char, _, _, self.right = script.get_char_list(self.delim)
        if char!=self.delim:
            raise SedException(script.position,'Missing delimiter {delim} for right parameter to command y', delim=self.delim)
        if not self.right:
            raise SedException(self.position,'Missing right parameter to command y')

        char = script.get_char()
        if not script.is_cmd_end():
            raise SedException(script.position,'Invalid extra characters after command y')
            
        try:
            if sys.version_info[0]==2:
                # python2
                self.translate = string.maketrans(self.left,self.right)  # @UndefinedVariable
            else:
                # python3
                self.translate = str.maketrans(self.left,self.right)
        except Exception as e:
            raise SedException(self.position,'Incorrect arguments to command y: {err}', err=str(e))

    def str_arguments(self):
        # source_chars, dest_chars = self.args
        return '{delim}{left}{delim}{right}{delim}'.format(
                   delim=self.delim,
                   left=self.left,
                   right=self.right)

    def apply(self, sed):
        sed.PS = sed.PS.translate(self.translate)
        return self.next
        
class Command_z(Command):
    def apply(self, sed):
        sed.PS = ''
        return self.next
        
COMMANDS = {'{': Command_block,
            '}': Command_block_end,
            ':': Command_label,
            'a': Command_a,
            'A': Command_A,
            'b': Command_b,
            'c': Command_c,
            'C': Command_C,
            'd': Command_d,
            'D': Command_D,
            '=': Command_equal,
            'F': Command_F,
            'g': Command_g,
            'G': Command_G,
            'h': Command_h,
            'H': Command_H,
            'i': Command_i,
            'I': Command_I,
            'l': Command_l,
            'n': Command_n,
            'N': Command_N,
            'p': Command_p,
            'P': Command_P,
            'q': Command_q,
            'Q': Command_Q,
            'r': Command_r,
            'R': Command_R,
            's': Command_s,
            't': Command_t,
            'T': Command_T,
            'w': Command_w,
            'v': Command_v,
            'W': Command_W,
            'x': Command_x,
            'y': Command_y,
            'z': Command_z,
        }

                
class Replacement(object):
    CASE_ASIS = '\\E'
    CASE_LOWER = '\\L'
    CASE_UPPER = '\\U'
    CASE_FLIP_NONE = '\\E'
    CASE_FLIP_LOWER = '\\l'
    CASE_FLIP_UPPER = '\\u'
    
    def __init__(self):
        self.string = ''
        self.cases = [ CaseSetter(self.CASE_ASIS,self.CASE_FLIP_NONE) ]

    def __str__(self):
        return self.string
        
    def __repr__(self):
        return '[ '+', '.join(repr(case) for case in self.cases)+' ]'
        
    def add_group(self,escaped,num):
        self.string += escaped
        self.cases[-1].add_part(num)
    
    def add_literal(self,escaped,string):
        self.string += escaped
        self.cases[-1].add_part(string)
        
    def add_escape(self,escaped,pyescaped):
        self.string += escaped
        if pyescaped in [ self.CASE_ASIS,self.CASE_LOWER,self.CASE_UPPER ]:
            self.add_case(pyescaped,self.CASE_FLIP_NONE)
        elif pyescaped in [ self.CASE_FLIP_LOWER,self.CASE_FLIP_UPPER ]:
            self.add_case(self.cases[-1].get_case_set(),pyescaped)
        else:
            self.cases[-1].add_part(int(re.match('\\(\\?:\\\\(\\d+)\\)',pyescaped).group(1)))

    def add_case(self,case_set,case_flip):
        if self.cases[-1].is_empty():
            self.cases.pop()
        self.cases.append(CaseSetter(case_set,case_flip))
            
    def expand(self, match):
        result = ''
        for case in self.cases:
            result += case.expand(match)
        return result
    
class CaseSetter(object):
    def __init__(self,case_set,case_flip):
        self.case_set = case_set
        self.case_set_fn = self.MAP.get(case_set)
        
        self.case_flip = case_flip
        self.case_flip_fn = self.MAP.get(case_flip)
        
        self.parts = []
        
    def __str__(self):
        return self.case_set+self.case_flip+''.join(
                    (part if type(part)==str
                          else '\\+str(part)')
                        for part in self.parts)
        
    def __repr__(self):
        return self.__str__()
    
    def is_empty(self):
        return len(self.parts)==0
    
    def get_case_set(self):
        return self.case_set
    
    def add_part(self,part):
        self.parts.append(part)
        
    def expand(self,match):
        txt = ''
        for part in self.parts:
            if type(part)==int:
                txt += match.group(part) or ''
            else:
                txt += part
        return self.case_flip_fn(self.case_set_fn(txt))
                        
    MAP = {
        Replacement.CASE_LOWER: (lambda txt: txt.lower()),
        Replacement.CASE_UPPER: (lambda txt: txt.upper()),
        Replacement.CASE_ASIS: (lambda txt: txt),
        Replacement.CASE_FLIP_LOWER: (lambda txt: txt[0].lower()+txt[1:] if txt else ''),
        Replacement.CASE_FLIP_UPPER: (lambda txt: txt[0].upper()+txt[1:] if txt else '')
        # CASE_FLIP_NONE: keep_as_is, ## same as CASE_ASIS!!!
    }
    
class SedRegexpEmpty(object):
    def __init__(self, position, delim, address=True):
        self.position = position
        self.delim = delim
        self.pattern = ''
        self.address = address
    
    def matches(self,strg):
        if SedRegexp.last_regexp is None:
            raise SedException(self.position, 'No regexp to match in place of empty regexp')
        return SedRegexp.last_regexp.matches(strg)
        
    def subn(self, replacement, strng, globally, count, sed_compatible):
        if SedRegexp.last_regexp is None:
            raise SedException(self.position, 'No regexp to match in place of empty regexp')
        return SedRegexp.last_regexp.subn(replacement, strng, globally, count, sed_compatible)
        
    def __str__(self):
        return ('' if self.delim=='/' or not self.address else '\\'
                +self.delim+self.delim)

    def __repr__(self):
        return self.__str__()
    
    def process_flags_and_dollars(self):
        pass
    
    def set_multi_line(self):
        raise SedException(self.position, 'Using multi-line flag with an empty regular expression is not possible')
        
    def set_ignore_case(self):
        raise SedException(self.position, 'Using ignore case flag with an empty regular expression is not possible')
        

class SedRegexp(object):
    last_regexp = None
    
    def __init__(self, position, delim, pattern, py_pattern, dollars, address=True):
        self.position = position
        self.delim = delim
        self.pattern = pattern
        self.py_pattern = py_pattern
        self.dollars = dollars
        self.address = address
        
        self.multi_line = False
        self.ignore_case = False
        self.flags = ''
        self.compiled = None
        
    def __str__(self):
        return self.toString()
    
    def toString(self):
        result = '' if self.delim=='/' else '\\'
        result += self.delim+self.pattern+self.delim
        if self.address:
            result += 'I' if self.ignore_case else ''
            result += 'M' if self.multi_line else ''
        return result

    def __repr__(self):
        return self.__str__()
        
    def set_multi_line(self):
        self.multi_line = True
        
    def set_ignore_case(self):
        self.ignore_case = True

    def process_flags_and_dollars(self):
        self.flags = '(?'
        if self.multi_line:
            self.flags += 'm'
        else:
            self.flags += 's'
        if self.ignore_case:
            self.flags += 'i'
        self.flags += ')'

        # We have to process the dollar signs from
        # the back to the front, because otherwise
        # the index of the dollar signs would not fit
        # anymore after our first change in the pattern.
        # Once we processed them - or if we do not have
        # sed compatibility requested, the list is empty!
        while len(self.dollars)>0:
            dollar = self.dollars.pop()
            if (dollar+1<len(self.py_pattern) and
                self.py_pattern[dollar+1] not in '|)'):
                # we have a dollar sign to be taken literally -> change to \\$ 
                self.py_pattern = self.py_pattern[0:dollar]+'\\'+self.py_pattern[dollar:]
            elif not self.multi_line:
                # we have a dollar sign but not multi-line -> change to \\Z
                self.py_pattern = self.py_pattern[0:dollar]+'\\Z'+self.py_pattern[dollar+1:]

        try:
            self.compiled = re.compile(self.flags+self.py_pattern)
        except re.error as e:
            raise SedException(self.position, 'Invalid regex {escaped}{delim}{pattern}{delim} (translated to """{py_pattern}"""): {err}',
                               escaped='' if self.delim=='/' else '\\',
                               delim=self.delim,
                               pattern=self.pattern,
                               py_pattern=self.flags+self.py_pattern,
                               err=str(e))

    def matches(self, strng):
        SedRegexp.last_regexp = self
        try:
            match = self.compiled.search(strng)
            return match is not None
        except Exception as e:
            raise SedException(self.position, 'Error when compiling regex {escaped}{delim}{pattern}{delim} (translated to """{py_pattern}"""): {err}',
                               escaped='' if self.delim=='/' else '\\',
                               delim=self.delim,
                               pattern=self.pattern,
                               py_pattern=self.flags+self.py_pattern,
                               err=str(e))

    def subn(self, replacement, strng, globally, count, sed_compatible):
        # re.sub() extended:
        # - an unmatched group returns an empty string rather than None
        #   (http://gromgull.net/blog/2012/10/python-regex-unicode-and-brokenness/)
        # - the nth occurrence is replaced rather than the nth first ones
        #   (https://mail.python.org/pipermail/python-list/2008-December/475132.html)
        # - since 3.5, first agument of _expand must be a compiled regex
        SedRegexp.last_regexp = self
        class Nth(object):
            def __init__(self):
                self.matches = 0
                self.prevmatch_end = -1
            def __call__(self, matchobj):
                try:
                    if (sed_compatible
                        and matchobj.group(0)==''
                        and matchobj.start(0)==self.prevmatch_end):
                        return ''
                    else:
                        self.matches += 1
                        if self.matches==count or globally and self.matches>count:
                            return replacement. expand(matchobj)
                        else:
                            return matchobj.group(0)
#                except Exception as e:
#                    print(e)
#                    raise e
                finally:
                    self.prevmatch_end = matchobj.end(0)
    
        try:
            strng_res, nsubst = self.compiled.subn(Nth(), strng, 0 if globally or sed_compatible else count)
        except re.error as e:
            raise SedException(self.position, 'Error substituting regex {escaped}{delim}{pattern}{delim} (translated to """{py_pattern}"""): {err}',
                               escaped='' if self.delim=='/' else '\\',
                               delim=self.delim,
                               pattern=self.pattern,
                               py_pattern=self.flags+self.py_pattern,
                               err=str(e))
    
        # nsubst is the number of subst which would
        # have been made without the redefinition
        return (nsubst >= count), strng_res
    
class AddressLast(object):
    def __init__(self,sed):
        self.sed = sed
        
    def __str__(self):
        return '$'
    
    def __repr__(self):
        return self.__str__()
        
    def matches(self):
        return self.sed.is_last_line()
        
        
class AddressZero(object):
    def __init__(self,sed):
        self.sed = sed
        
    def __str__(self):
        return '0'
        
    def __repr__(self):
        return self.__str__()
        
    def matches(self):
        return True
        
        
class AddressRegexp(object):
    def __init__(self, sed, regexp):
        self.sed = sed
        self.regexp = regexp
    
    def __str__(self):
        return str(self.regexp)
        
    def __repr__(self):
        return self.__str__()
        
    def matches(self):
        return self.regexp.matches(self.sed.PS)
        
        
class AddressNum(object):
    def __init__(self, sed, num):
        self.sed = sed
        self.num = num
        
    def __str__(self):
        return str(self.num)
        
    def __repr__(self):
        return self.__str__()
        
    def matches(self):
        return self.sed.file_line_no()==self.num
        
        
class AddressStep(object):
    def __init__(self, sed, num, step):
        self.sed = sed
        self.num = num
        self.step = step
        
    def __str__(self):
        return str(self.num)+'~'+str(self.step)
        
    def __repr__(self):
        return self.__str__()
        
    def matches(self):
        line_no = self.sed.file_line_no()
        if line_no<self.num:
            return False
        return (line_no-self.num)%self.step==0
        

class AddressRangeNone(object):
    def __init__(self):
        self.first_line = True
    
    def is_active(self):
        return True
        
    def __str__(self):
        return ''
            
    def __repr__(self):
        return ''
        
    def from_as_str(self):
        return ''
        
    def to_as_str(self):
        return ''
        
    def negated_as_str(self):
        return ''
        
        
class AddressRangeFake(object):
    def __init__(self, from_addr):
        self.from_addr = from_addr
        self.first_line = True
        self.set_negate(False)
        
    def set_negate(self, negate):
        self.active_return = not negate
        self.inactive_return = negate

    def is_active(self):
        if self.from_addr.matches():
            return self.active_return
        else:
            return self.inactive_return
            
    def __str__(self):
        return str(self.from_addr)+self.negated_as_str()
            
    def __repr__(self):
        return self.__str__()
        
    def from_as_str(self):
        return str(self.from_addr)
        
    def to_as_str(self):
        return ''
        
    def negated_as_str(self):
        if self.active_return:
            return ''
        else:
            return '!'
            

class AddressRange(object):
    def __init__(self, from_addr, exclude):
        self.from_addr = from_addr
        self.sed = self.from_addr.sed
        self.exclude = exclude
        self.active = False
        self.set_negate(False)
        
    def set_negate(self, negate):
        self.first_line_default = negate
        self.first_line = self.first_line_default
        self.exclude_return = self.exclude==negate
        self.active_return = not negate
        self.inactive_return = negate
        
    def __str__(self):
        return (self.from_as_str()+','+
                self.to_as_str()+
                self.negated_as_str())
        
    def __repr__(self):
        return self.__str__()
        
    def from_as_str(self):
        return str(self.from_addr)
        
    def to_as_str(self):
        return '---'
        
    def negated_as_str(self):
        if self.active_return:
            return ''
        else:
            return '!'
            
    def exclude_as_str(self):
        if self.exclude:
            return '-'
        else:
            return ''
        
class AddressRangeToNum(AddressRange):
    def __init__(self, from_addr, num, exclude):
        super(AddressRangeToNum,self). __init__(from_addr, exclude)
        self.num = num 
        self.last_line_no = 0
        
    def is_active(self):
        if self.active:
            self.first_line = self.first_line_default
            curr_line_no = self.sed.file_line_no()
            if self.last_line_no<curr_line_no:
                self.active = False
                return self.inactive_return
            elif self.last_line_no == curr_line_no:
                self.active = False
                return self.exclude_return
            else:
                return self.active_return
        elif self.from_addr.matches():
            self.first_line = True
            self.last_line_no = self.calc_last_line()
            self.active = True
            return self.active_return
        else:
            return self.inactive_return
            
    def calc_last_line(self): # num
        return self.num
        
    def to_as_str(self):
        return self.exclude_as_str()+str(self.num)
        
        
class AddressRangeToCount(AddressRangeToNum):
    def calc_last_line(self): # count
        return self.sed.file_line_no()+self.num
    def to_as_str(self):
        return self.exclude_as_str()+'+'+str(self.num)
    
class AddressRangeToMultiple(AddressRangeToNum):
    def calc_last_line(self):
        line_no = self.sed.file_line_no()
        return line_no+self.num-(line_no%self.num)
    def to_as_str(self):
        return self.exclude_as_str()+'~'+str(self.num)
        
class AddressRangeToLastLine(AddressRange):
    def is_active(self):
        if self.active:
            self.first_line = self.first_line_default
            if self.sed.is_last_line():
                self.active = False
                return self.exclude_return
            else:
                return self.active_return
        elif self.from_addr.matches():
            self.first_line = True
            self.active = True
            return self.active_return
        else:
            return self.inactive_return
            
    def to_as_str(self):
        return self.exclude_as_str()+'$'
                
class AddressRangeZeroToRegexp(AddressRange):
    def __init__(self, from_addr, regexp, exclude):
        super(AddressRangeZeroToRegexp,self). __init__(from_addr, exclude)
        self.regexp = regexp
        self.active = True
        self.next_first_line = True
    
    def is_active(self):
        if self.active:
            self.first_line = self.next_first_line
            self.next_first_line = False
            if self.regexp.matches(self.sed.PS):
                self.active = False
                return self.exclude_return
            else:
                return self.active_return
        else:
            self.first_line = True
            return self.inactive_return
 
    def to_as_str(self):
        return self.exclude_as_str()+str(self.regexp)
        
class AddressRangeToRegexp(AddressRange):
    def __init__(self, from_addr, regexp, exclude):
        super(AddressRangeToRegexp,self). __init__(from_addr, exclude)
        self.regexp = regexp
    
    def is_active(self):
        if self.active:
            self.first_line = self.first_line_default
            if self.regexp.matches(self.sed.PS):
                self.active = False
                return self.exclude_return
            else:
                return self.active_return
        elif self.from_addr.matches():
            self.first_line = True
            self.active = True
            return self.active_return
        else:
            return self.inactive_return
            
    def to_as_str(self):
        return self.exclude_as_str()+str(self.regexp)


class SedException(Exception):
    def __init__(self, position, message, **params):
        self.message = 'sed.py error: %s: %s' % (position,message.format(**params))
    def __str__(self):
        return self.message


# -- Main -------------------------------------------


def do_helphtml():
    if os.path.isfile('sed.html'):
        helpfile = 'sed.html'
    else:
        helpfile = r'http://sed.godrago.net/sed.html'

    webbrowser.open(helpfile, new=2)
    
class Filename(object):
    def __init__(self, filename):
        self.filename = filename

def script_string_arg(strng):
    return strng
    
def script_file_arg(strng):
    return Filename(strng)
        
def parse_command_line():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=BRIEF,
        epilog="""Options -e and -f can be repeated multiple times and add to the commands executed for each line of input in the sequence they are specified.

If neither -e nor -f is given, the first positional parameter is taken as the script, as if it had been prefixed with -e.""")
        
    parser.add_argument(
        '-H', '--htmlhelp',
        help='open html help page in web browser',
        action='store_true',
        default=False,
        dest='do_helphtml')
        
    parser.add_argument(
        "-v",
        help="display version",
        action="store_true",
        default=False,
        dest="version")
        
    parser.add_argument(
        '-f', '--file',
        help="add script commands from file",
        action="append",
        dest="scripts",
        default=[],
        type=script_file_arg,
        metavar='file')
    
    parser.add_argument(
        '-e', '--expression',
        help="add script commands from string",
        action="append",
        dest="scripts",
        default=[],
        type=script_string_arg,
        metavar='string')
        
    parser.add_argument(
        '-i', '--in-place',
        nargs='?',
        help="change input files in place",
        dest="in_place",
        metavar='backup suffix',
        default=None)
        
    parser.add_argument(
        "-n", '--quiet', '--silent',
        help="print only if requested",
        action="store_true",
        default=False,
        dest="no_autoprint")
        
    parser.add_argument(
        "-s", '--separate',
        help="consider input files as separate files instead of a continuous strem",
        action="store_true",
        default=False,
        dest="separate")
    
    parser.add_argument(
        "-p", '--python-syntax',
        help="Python regexp syntax",
        action="store_false",
        default=True,
        dest="sed_compatible")
    
    parser.add_argument(
        "-r", '-E', '--regexp-extended',
        help="extended regexp syntax",
        action="store_true",
        default=False,
        dest="regexp_extended")
    
    parser.add_argument(
        '-l', '--line-length',
        help="line length to be used by l command",
        dest="line_length",
        default=70,
        type=int)
    
    parser.add_argument(
        "-d", "--debug",
        help='dump script and annotate execution on stderr',
        action="store",
        type=int,
        default=0,
        dest="debug")
    
    parser.add_argument(
        "targets",
        nargs='*',
        help='files to be processed (defaults to stdin if not specified)',
        default=[])

    args = parser.parse_args()
    if (len(args.scripts)==0 and
            len(args.targets)==0):
        parser.print_help()
        raise SedException('','No script specified')

    return args

def main():
    exit_code = 0

    try:
        args = parse_command_line()
        
        if args.version:
            print(BRIEF)
            print(VERSION)
            return
        elif args.do_helphtml:
            do_helphtml()
            return
        
        sed = Sed()
        sed.no_autoprint = args.no_autoprint
        sed.regexp_extended = args.regexp_extended
        sed.in_place = args.in_place
        sed.line_length = args.line_length
        sed.debug = args.debug
        sed.separate = args.separate
        sed.sed_compatible = args.sed_compatible
        
        targets = args.targets
        scripts = args.scripts
        if len(scripts)==0:
            # at this point we know targets is
            # not empty because that was checked
            # in parse_command_line() already
            scripts = [ targets.pop(0) ]
            
        for script in scripts:
            if isinstance(script,Filename):
                sed.load_script(script.filename)
            else:
                sed.load_string(script)
                
        sed.apply(targets)
        exit_code = sed.exit_code
        
    except SedException as e:
        print(e.message, file=sys.stderr)
        exit_code = 1
        
    except:
        traceback.print_exception(*sys.exc_info(),file=sys.stderr)
        exit_code = 1
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
