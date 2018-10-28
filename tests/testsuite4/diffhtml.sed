#!/bin/sh
#
# Beautifies the output of diff -Nur to the HTML format
# needs the expand utility to convert tabs to spaces, to preserve 
# identation. Output HTML Code is pretty worse i think and the
# colors suck somehow
#
# Sat Apr 14 21:59:36 CEST 2001
# by Tilmann Bitterberg

### sh lines commented to test sed script
###expand |
###sed '
s/>/\&gt;/g;   s/</\&lt;/g
s|ü|\&uuml;|g; s|Ü|\&Uuml;|g; s|ä|\&auml;|g
s|Ä|\&Auml;|g; s|ö|\&ouml;|g; s|Ö|\&Ouml;|g
s|ß|\&szlig;|g

s/^+$/+ /
s/^-$/- /
s/^$/ /
/^[-+]/!s/$/<BR>/

1i\
<HTML><HEAD></HEAD><BODY bgcolor=white>

/^diff /{i\
<P>
s|[^/]*/||
s| .*||
s|.*|<font color=white><TT>&</TT></FONT>|
s|.*|<table border=0 cellspacing=0 width=100% bgcolor=#057205><TR><TD>&</TD></TR></TABLE><P>|
}

# Could be done in one line
/^@@ /{
s|^@@|<font color=red><TT>@@|
s|$|</TT></FONT>|
}

\|^---|s|.*|<TT><font color=lightblue>&</FONT></TT><BR>|
\|^+++|s|.*|<TT><font color=darkblue>&</FONT></TT><BR>|

# Take care of removed lines
/^-[^-]/{i\
<table border=0 cellspacing=0 width=100% bgcolor=#eddcdc><TR><TD>\
<TT><FONT color=darkred>
:a
N
s/\n-/||||/
ta
h
s/.*\n//
/<BR>$/!s/$/<BR>/
x
s/\(.*\)\n[^\n]*$/\1/
s/||||/<BR>\
-/g
:space1
/  /{
  s|  |\&nbsp; |
  bspace1
}
s|$|</FONT></TT></TD></TR></TABLE>|p
x
}

# Take care of added lines
/^+[^+]/{i\
<table border=0 cellspacing=0 width=100% bgcolor=#dbf7ff><TR><TD>\
<TT><FONT color=darkblue>
:b
N
s/\n+/||||/
tb
h
s/.*\n//
/<BR>$/!s/$/<BR>/
x
s/\(.*\)\n[^\n]*$/\1/
s/||||/<BR>\
+/g
:space2
/  /{
  s|  |\&nbsp; |
  bspace2
}
s|$|</FONT></TT></TD></TR></TABLE>|p
x
}

# We need to do this, because we only want the spaces at the beginning

:c
/^Ä\+[^ ][-_A-Za-z0-9]/bend
s/^\(Ä*\) /\1Ä/
tc

:end
s/Ä/\&nbsp;/g
/^&nbsp;/{
  s|^|<TT>|
  s|$|</TT>|
}

:space3
/  /{
  s|  |\&nbsp; |
  bspace3
}

$a\
</PRE></BODY></HTML>
###' # sed done
