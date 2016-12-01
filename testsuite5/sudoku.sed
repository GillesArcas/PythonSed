#!/usr/bin/sed -nrf

##
## Usage: ./sudoku.sed -i puzzle.dat
##
## Bugs: avati@gluster.com
##

##
##  amp:~$ cat puzzle.dat
##  7 _ _  _ 9 _  _ _ 3
##  _ _ 5  8 _ 2  6 _ _
##  _ 8 _  3 _ 1  _ 9 _
##  _ 5 _  7 _ 4  _ 1 _
##  3 _ _  _ _ _  _ _ 4
##  _ 4 _  5 _ 9  _ 8 _
##  _ 2 _  9 _ 8  _ 5 _
##  _ _ 9  6 _ 7  4 _ _
##  5 _ _  _ 2 _  _ _ 8
##
##  amp:~$ ./sudoku.sed -i puzzle.dat
##
##  amp:~$ cat puzzle.dat
##  7 6 1 4 9 5 8 2 3
##  9 3 5 8 7 2 6 4 1
##  4 8 2 3 6 1 7 9 5
##  2 5 6 7 8 4 3 1 9
##  3 9 8 2 1 6 5 7 4
##  1 4 7 5 3 9 2 8 6
##  6 2 3 9 4 8 1 5 7
##  8 1 9 6 5 7 4 3 2
##  5 7 4 1 2 3 9 6 8
##


##
##   Algorithm
##
## - Input matrix is converted into a 1-d list of nodes into the pattern space
##
## - Each node is a list of possible numbers for that position in parantheses
##   E.g (13456) - position with these possible values
##       (2) - position fixed with value 2
##
## - Underscore indicates empty/unfilled positions and are converted to
##    (123456789)
##
## - Column consistencies are implemented with regexes comparing positions
##   separated by 9 nodes
##
## - Row consistencies and Block consistencies are implemented by 'marking'
##   one set of nodes at a time, by changing the parantheses to <>, applying
##   the consistency restrictions into the subset, and unmarking them back
##   to parantheses
##
## - Column, Row and Block consistencies are applied in a loop till there
##   are no two consequent numbers in the pattern space
##

#######################

b Read_Input

#######################

:Read_Input

#/^#%/ {
#      s/^#%//
#      H
#}

/^[1-9\ _#%]+$/ {
      s/^#%//
      H
}

$ {
  g
  b Fix_Whitespaces
}
n
b Read_Input

#######################

:Fix_Whitespaces
s/[ \t\n]+/ /g
s/^ +//
s/ *$/ /
b Normalize

#######################

:Normalize
s/([^ ])/\(\1\)/g
s/_/123456789/g
b Main_Loop

#######################

:Main_Loop

## check if content of hold space and pattern space are the same
## (i.e last run of attempts changed nothing -- no further hope)

s/^(.)/\|\1/
H
x

s/[ \t\n\r]+/ /g


## let the previous s// not affect the following check
t Right_Here
:Right_Here

s/^(.*)\|\1/\1/
t Display9
s/^.*\|//
h


b Fix_Rows

#/[1-9]{2}/ {
#            b Fix_Rows
#}
#b Display9

#######################

:Fix_Columns

# s/\(([1-9])\) ((([^ ]+ ){8})([^ ]+ ){9}*)([^ ]+)\1([^ ]+)/\(\1\) \2\6\7/
# s/([^ ]+)([1-9])([^ ]+) ((([^ ]+ ){8})([^ ]+ ){9}*)\(\2\)/\1\3 \4\(\2\)/
s/\(([1-9])\) ((([^ ]+ ){8})(([^ ]+ ){9})*)([^ ]+)\1([^ ]+)/\(\1\) \2\7\8/
s/([^ ]+)([1-9])([^ ]+) ((([^ ]+ ){8})(([^ ]+ ){9})*)\(\2\)/\1\3 \4\(\2\)/
t Fix_Columns

b Fix_Blocks

#######################

:Fix_Rows

### Row 0

s/(([^ ]+ ){9}{0}([^ ]+ ){3}{0})\(([^\)]+)\) \(([^\)]+)\) \(([^\)]+)\)/\1<\4> <\5> <\6>/
s/(([^ ]+ ){9}{0}([^ ]+ ){3}{1})\(([^\)]+)\) \(([^\)]+)\) \(([^\)]+)\)/\1<\4> <\5> <\6>/
s/(([^ ]+ ){9}{0}([^ ]+ ){3}{2})\(([^\)]+)\) \(([^\)]+)\) \(([^\)]+)\)/\1<\4> <\5> <\6>/

:Fix_a_Row

s/(.*)<([1-9])>(.*<[^<>]*)\2(.*)/\1<\2>\3\4/
s/(.*<[^<>]*)([1-9])(.+)<\2>(.*)/\1\3<\2>\4/

t Fix_a_Row

## Last Row?

/> *$/b Rows_Done


## Next Row

:Next_Row_loop
s/<([^ ]+ ([^ ]+ ){8})\(/\(\1\{/g
s/>( ([^ ]+ ){8}[^ ]+)\)/\)\1\}/g
t Next_Row_loop

y/\{\}/<>/

b Fix_a_Row

###

:Rows_Done
y/<>/\(\)/

b Fix_Columns

#######################

:Fix_Blocks

### Block 0

s/(([^ ]+ ){27}{0}([^ ]+ ){3}{0})\(([^\)]+)\) \(([^\)]+)\) \(([^\)]+)\)/\1<\4> <\5> <\6>/
s/(([^ ]+ ){27}{0}([^ ]+ ){3}{3})\(([^\)]+)\) \(([^\)]+)\) \(([^\)]+)\)/\1<\4> <\5> <\6>/
s/(([^ ]+ ){27}{0}([^ ]+ ){3}{6})\(([^\)]+)\) \(([^\)]+)\) \(([^\)]+)\)/\1<\4> <\5> <\6>/


:Fix_a_Block

s/(.*)<([1-9])>(.*<[^<>]*)\2(.*)/\1<\2>\3\4/
s/(.*<[^<>]*)([1-9])(.+)<\2>(.*)/\1\3<\2>\4/
t Fix_a_Block

## Last block ?

/> *$/b Blocks_Done


## Last block in row ?

/> (([^ ]+ ){27}+)$/b Fresh_Row

## Next block in same row

:Next_Block_Same_Row_loop
s/<([^ ]+ ([^ ]+ ){2})\(/\(\1\{/g
s/>( ([^ ]+ ){2}[^ ]+)\)/\)\1\}/g
t Next_Block_Same_Row_loop

y/\{\}/<>/

b Fix_a_Block

## Next block in fresh row

:Fresh_Row

:Next_Block_Fresh_Row_loop
s/<([^ ]+ ([^ ]+ ){20})\(/\(\1\{/
s/>( ([^ ]+ ){20}[^ ]+)\)/\)\1\}/
t Next_Block_Fresh_Row_loop

y/\{\}/<>/

b Fix_a_Block

:Blocks_Done

y/<>/\(\)/

b Main_Loop

#######################

:Display9

s/(([^ ]+ ){9})/\1\n/g
s/\([0-9][0-9]+\)/_/g
s/\(([1-9])\)/\1/g
p
q
