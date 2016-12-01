#Helloman 5.10.06
#Use it as you want to.

#Z is border field - used to have universal counting algorithm
#X means there was no cell before
#x means there was one
#y states that cell needs to be done
#Y is done
#| is used as a counter char inside (instead of placeholder) [zXx]<++>[yY]

s/|$//
s/^\(.\{20\}\).*$/\1/
p
#cut off what is not needed
#note: shorter input leads to mistakes 8-)
1h
1!H
$!{d;b}
g
#one border cell for upper line and one for lower
s/\n/ZYZY/g 
#for 20x20 we need 22 border cells up and down
s/^/ZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZY/
s/$/ZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZYZY/
s/ /XY/g
s/#/xy/g
:count
# three upper cells
s/\([XxZ]\)\([|]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[XxZ][|]*y\)/\1|\2/
s/\([XxZ]\)\([|]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[XxZ][|]*y\)/\1|\2/
s/\([XxZ]\)\([|]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[^Y]*Y[XxZ][|]*y\)/\1|\2/
# one on the left and on the right
s/\([XxZ]\)\([|]*Y[XxZ][|]*y[XxZ]\)\([|]*[yY]\)/\1|\2|\3/
# three cells below
s/\([XxZ][|]*y[^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][XxZ]\)\([|]*[yY]\)/\1|\2/
s/\([XxZ][|]*y[^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][XxZ]\)\([|]*[yY]\)/\1|\2/
s/\([XxZ][|]*y[^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][^yY]*[yY][XxZ]\)\([|]*[yY]\)/\1|\2/

#we have finished with this cell one
s/y/Y/
tcount
#get rid of border lines
s/Z[|]*Y//g

#counts the |||| and makes results
s/X[|]\{0,2\}Y/ /g
s/x[|]\{0,1\}Y/ /g
s/x[|]\{2\}Y/#/g
s/[Xx][|]\{3\}Y/#/g
s/[Xx][|]\{4,\}Y/ /g

#format the output
s/.\{20\}/&|\n/g

#:wq
