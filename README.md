# PythonSed
A full and working Python implementation of sed

[![Build Status](https://travis-ci.org/GillesArcas/PythonSed.svg?branch=master)](https://travis-ci.org/GillesArcas/PythonSed)

[![Coverage Status](https://coveralls.io/repos/github/GillesArcas/PythonSed/badge.svg?branch=master)](https://coveralls.io/github/GillesArcas/PythonSed?branch=master)
### Contents

* * *

[General Information](#general-information)

[Usage as a command line utility](#usage-as-a-command-line-utility)

[Usage as a Python module](#usage-as-a-python-module)

[Sed dialect](#sed-dialect)

[Testing](#testing)

[Timing](#timing)

[To do list](#to-do-list)

* * *

### General Information

* * *

#### Description

`pythonsed` is a full and working Python implementation of sed. Its reference is GNU sed 4.8 of which it implements nearly all commands and features. It may be used as a command line utility or it can be used as a module to bring sed functionality to Python scripts.

A complete set of tests is available as well as a testing utility. These tests include scripts from various origins and cover all aspects of sed functionalities.

* * *

#### Compatibility


| Version                    |  Status                                                      |
| -------------------------- | ------------------------------------------------------------ |
| Python 3.8                 | Fully compatible                                             |
| Python 3.7                 | Fully compatible even for s///g with zero length matches. See this [question at stackoverflow](https://stackoverflow.com/questions/53642571/retrieving-python-3-6-handling-of-re-sub-with-zero-length-matches-in-python-3) |
| Python 3                   | Fully compatible                                             |
| Python 2.7.4 and above     | Fully compatible                                             |
| Python 2.7 to Python 2.7.3 | Fully compatible except regexps of the form ((.\*)\*). This causes one of the script from Chang suite to fail. |
| Python 2.6                 | Fully compatible except regexps of the form ((.\*)\*). argparse module must be installed. |
| Python 2.5 and below       | Not tested                                                   |

Compatibility status applies also to the testing utility `test-suite.py`.

* * *

#### License

`PythonSed` is released under the MIT license.

------

### Install

------

To install, just clone or download the repository zip file and run the setup in download directory:

```
pip install .
```
This installs a command line utility named `pythonsed` and a package named `PythonSed`. 

***

### Usage as a command line utility

------

`pythonsed` is as console program receiving information from the command line. The format of the command line identical to that of GNU sed version 4.8 with the addition of the option -p or --python-syntax, which allows to specify Python regular expressions instead of the less powerful sed variant:

```
usage: sed.py [-h] [-H] [-v] [-f file] [-e string] [-i [backup suffix]] [-n]
              [-s] [-p] [-r] [-l LINE_LENGTH] [-d]
              [targets [targets ...]]

sed.py - python sed module and command line utility

positional arguments:
  targets               files to be processed (defaults to stdin if not
                        specified)

optional arguments:
  -h, --help            show this help message and exit
  -H, --htmlhelp        open html help page in web browser
  -v                    display version
  -f file, --file file  add script commands from file
  -e string, --expression string
                        add script commands from string
  -i [backup suffix], --in-place [backup suffix]
                        change input files in place
  -n, --quiet, --silent
                        print only if requested
  -s, --separate        consider input files as separate files instead of a
                        continuous strem
  -p, --python-syntax   Python regexp syntax
  -r, -E, --regexp-extended
                        extended regexp syntax
  -l LINE_LENGTH, --line-length LINE_LENGTH
                        line length to be used by l command
  -d, --debug           dump script and annotate execution on stderr

Options -e and -f can be repeated multiple times and add to the commands
executed for each line of input in the sequence they are specified.

If neither -e nor -f is given, the first positional parameter is taken
as the script, as if it had been prefixed with -e.
```

`pythonsed` may also use redirection to receive its input or send its output with the usual syntax:

`cat myfile | pythonsed -f myscript1.sed | pythonsed -f myscript2.sed > myresultfile`

It is also possible for `pythonsed` to receive its input from the keyboard by omitting any input file:

`pythonsed -f myscript.sed`

* * *

### Usage as a Python module

* * *

An example covering all necessary symbols:

```python
from PythonSed import Sed, SedException

sed = Sed()
try:
    sed.no_autoprint = True
    sed.regexp_extended = False
    sed.load_script('myscript.sed')
    sed.apply('myinput.txt')
except SedException as e:
    print(e.message)
except:
    raise
```

`sed.apply()`  input parameter may be a string (which is interpreted as a filename) or file-like object (including streams). Note that `sed.apply()` returns the list of lines printed by the script. As a default, these lines are printed to stdout. `sed.apply()` has an output parameter which enables to inhibit printing the lines (`output=None`) or enables to redirect the output to some text file (`output='somefile.txt'`) or to a file-like object (including streams). Note also that if myinput or myoutput are file-like objects, they must be closed by the caller.

The script is given to sed by one or more calls to `sed.load_string(my_script_string)` and/or  `sed.load_script(my_script_file)` where my_script_file can be either a file name or a file-like object (including streams). The final script is the concatination of what was given in the various calls to `load_string` and `load_script` in the sequence of the calls.

The available attributes and their defaults are:

<table border="1">
<tr><th align="left">Attribute</th><th align="left">Default</th></tr>
<tr><td>encoding</td>        <td>'latin-1'</td></tr>
<tr><td>line_length</td>     <td>70</td></tr>
<tr><td>no_autoprint</td>    <td>False</td></tr>
<tr><td>regexp_extended</td> <td>False</td></tr>
<tr><td>sed_compatible</td>  <td>True</td></tr>
<tr><td>in_place</td>        <td>None</td></tr>
<tr><td>separate</td>        <td>False</td></tr>
<tr><td>debug</td>           <td>0..3</td></tr>
</table>

They can all be specified as named parameters on the constructor of the Sed object or set individually before the call to `apply()`, which can be called multiple times on the same Sed object with changing attributes in between. The script can only be appended to after the creation of the Sed object and subsequent calls to `apply()` will re-compile the extended script before applying it to the input.

* * *

### sed dialect

* * *

`PythonSed` implements all standard commands and regular expression features of sed. Its reference is GNU sed 4.8. It implements all its features except for character classes (no support in Python for those) and
the GNU sed specific command e. 

GNU sed [manual](http://www.gnu.org/software/sed/manual/sed.html) page can serve as a reference for `PythonSed`.

* * *


#### Addresses

<table>
    <tr>
        <td width=150><code>number</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>$</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>/regexp/</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>/regexp/I</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>\%regexp%</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>address,address</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>address!</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>0,/regexp/</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>first~step</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>addr1,+N</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>addr1,~N</code></td><td>standard behavior</td>
    </tr>
</table>

#### Regular expressions

<table>
    <tr>
        <td width=150><code>char</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>*</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>\+</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>\?</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>\{i\} \{i,j\} \{i,\}</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>\(regexp\)</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>.</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>^</code></td><td>standard behavior. When not at start of regexp, matches as itself</td>
    </tr>
    <tr>
        <td><code>$</code></td><td>standard behavior. When not at end of regexp, matches as itself</td>
    </tr>
    <tr>
        <td><code>[list] [^list]</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>regexp1\|regexp2</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>regexp1regexp2</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>\digit</code></td><td>standard behavior (back reference)</td>
    </tr>
    <tr>
        <td><code>textual escapes like \n and \t</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>functional escapes like \s, \S, \&lt; and \w</code></td><td>standard behavior</td>
    </tr>
    <tr>
        <td><code>\char</code></td><td>standard behavior (disable special regexp characters)</td>
    </tr>
</table>


Note that for any combination of quantifiers (\*, +, ?, {}), consecutive quantifiers or a quantifier starting a regexp will produce an error. This is true in basic or extended regular expression modes.

* * *

#### Extended regular expressions

Using the -r switch enables to simplify regular expressions by removing the backslash character before the special characters +, ?, (, ), |, { and }. If these characters must appear as regular characters in a regexp, they must be backslashed.

* * *

#### Commands

<table>
    <tr>
        <td width=150><code>a\<br/>text</code></td><td width=250>Compliant</td><td width=500>(including one liner syntax and double address extensions)</td>
    </tr>
    <tr>
        <td><code>b label</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>: label</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>c\<br/>text</code></td><td>Compliant</td><td>(including single line and double address extensions)</td>
    </tr>
    <tr>
        <td><code>d</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>D</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>=</code></td><td>Compliant</td><td>(including double address extension)</td>
    </tr>
    <tr>
        <td><code>g</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>G</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>h</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>H</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>i\<br/>text</code></td><td>Compliant</td><td>(including single line and double address extensions)</td>
    </tr>
    <tr>
        <td><code>l</code></td><td>Compliant</td><td>(length parameter not implemented)</td>
    </tr>
    <tr>
        <td><code>n</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>N</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>p</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>P</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>q</code></td><td>Compliant</td><td>(except exit code extension)</td>
    </tr>
    <tr>
        <td><code>r filename</code></td><td>Compliant</td><td>(including double address extension but not reading from stdin)</td>
    </tr>
    <tr>
        <td><code>s</code></td><td>Compliant</td><td>(including escape sequences in replacement (\L, \l, \U, \u, \E), modifiers M/m and combination of modifier g and number, but excluding modifier e)</td>
    </tr>
    <tr>
        <td><code>t label</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>w filename</code></td><td>Compliant</td><td>(including double address extension but not writing to stdout or stderr)</td>
    </tr>
    <tr>
        <td><code>x</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>y</code></td><td>Compliant</td><td>&nbsp;</td>
    </tr>
    <tr>
        <td><code>#</code></td><td>Compliant</td><td>(comments start anywhere in the line.)</td>
    </tr>
</table>


Compliant means compliant with <a href="https://www.gnu.org/software/sed/manual/html_node/Other-Commands.html#Other-Commands">GNU sed description</a>.

* * *

### Testing

* * *

#### Description

The working of `PythonSed` is tested and compared to the behavior of GNU sed with a set of tests and a testing utility.

The tests are either coded in text files with .suite extension or may be stored in test directories as standard sed scripts.

The test suites are:

<table>
    <tr>
    <td width=150><code>unit.suite</code></td><td>a text file containing unitary tests</td>
    </tr>
    <tr>
    <td><code>chang.suite</code></td><td>a text file containing scripts from <a href="http://www.rtfiber.com.tw/~changyj/sed/">Roger Chang web site</a></td>
    </tr>
    <tr>
        <td><code>test-suite1</code></td><td>a set of scripts from <a href="ftp://ftp.gnu.org/gnu/sed/">GNU sed test suite</a></td>
    </tr>
    <tr>
        <td><code>test-suite2</code></td><td>a set of scripts from the <a
        href="http://sed.sourceforge.net/grabbag/">seder's grab-bag</a>, <a
        href="http://rosettacode.org/wiki/Rosetta_Code">Rosetta code web site</a> and GitHub (<a href="http://github.com/shinh/sedlisp">lisp</a>!)</td>
    </tr>
    <tr>
        <td><code>test-suite3</code></td><td>additional unitary tests better stored in a folder with some extra data text files</td>
    </tr>
    <tr>
        <td><code>test-suite4</code></td><td>a set of scripts from the <a
        href="http://http://sed.sourceforge.net/">sed $HOME</a></td>
    </tr>
</table>
Note that the goal of these tests is not to check the correctness of the scripts but to verify that `sed.py` and GNU sed have the same behavior.

* * *

#### Testing utility

Tests are launched and checked with the `test-suite.py` Python script. This script uses either `PythonSed` package to run the sed scripts, or any sed executable. This enables to compare the working of `PythonSed` with the one of GNU sed.

The calling syntax is:

```
test-suite.py <testsuite> [number] [-b executable] [-x list of script references]
```

| Parameters                  |                                                              |
| --------------------------- | ------------------------------------------------------------ |
| `testsuite`                 | either a text file with .suite extension or a test directory |
| `number`                    | an optional reference number of a test, when present only this tests is run |
| `executable`                | an optional name or path of a sed executable to use for testing |
| `list of script references` | an optional list of tests to exclude for instance when a feature is not implemented. A script reference is either the title of the test for tests stored in modules, or the the name of the script file. |

* * *

#### Text file test suites

When tests are stored in a text file (with .suite extension), they are made of four elements:

*   the title of the test
*   the script itself
*   the input list of lines
*   the expected result

The four elements of a test are separated with lines made of three identical characters, for instance:

```
---
Test substitution with global flag
---
s/an/AN/g
---
In Xanadu did Kubhla Khan
---
In XANadu did Kubhla KhAN
---
```

Note also that:

*   the script section may be empty, enabling to test a script on various data without repeating the script.
*   The input and output sections may be empty, enabling to test various scripts on the same data, without repeating the data.
*   Flags are set with a comment on the first line. As usual, #n stops autoprint mode and extended regexp mode is set with #r or #nr.
*   The expected result may be ??? when the test has no result and ends with an error.
*   All text outside the test, i.e. before first delimiter or after last delimiter, is ignored and acts like a comment.


#### Directory test suites

When tests are stored in a directory, they are represented by three or four files with same name but different extensions:

*   the script itself, with '.sed' extension
*   the input of the script, with '.inp' extension
*   the expected result of the script, with '.good' extension
*   possibly a file, with '.flags' extension, containing the sed switches -n and/or -r.

Some other files may be used when using reading or writing commands in scripts. In that case, the expected written files must be named with extension '.wgoodN' where N is the number of the expected written file.

* * *

### Timing

* * *

A python implementation of sed has to face legitimate questions about timing. Fortunately, results are not bad. Unfortunately, they seem correlated with version number. Timings are given in seconds.

| Platform                                     | GNU sed 4.2.1 | sed.py python 2.6 | sed.py python 2.7 | sed.py python 3.4 |
| -------------------------------------------- | ------------- | ----------------- | ----------------- | ----------------- |
| Windows7, Intel Xeon 3.2 GHz, 6 Gb RAM       | 19.4          | 19.1              | 22.6              | 26.9              |
| Windows XP, Intel Pentium4 3.2 GHz, 4 Gb RAM | 47.5          | 50.7              | 56.5              | 71.2              |
| Linux, Intel Pentium4 3.2 GHz, 4 Gb RAM      | \-            | \-                | 51.0              | \-                |

Test conditions:

*   Only script files are used (scripts from folders testsuiteN). This is to avoid measuring the time to extract scripts, inputs and results from .suite files.
*   The given values are averaged from three consecutive test runs.

* * *

### To do list

* * *

At one moment, one has to decide what will be in the release to come, and what can be delayed. Here are some features which would be nice to have but can be delayed to a future version.

*   Better error handling when testing (the error message could be tested)
*   Use PythonSed as a basis for a sed debugger.
*   ...
