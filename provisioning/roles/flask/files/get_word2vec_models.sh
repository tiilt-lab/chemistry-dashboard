#!bin/bash
rm -f 
#OUTPUT=$( wget --save-cookies cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=0B7XkCwpI5KDYNlNUTTlSS21pQmM' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/Code: \1\n/p' )
#CODE=${OUTPUT##*Code: }
#wget --load-cookies cookies.txt 'https://docs.google.com/uc?export=download&confirm='$CODE'&id=0B7XkCwpI5KDYNlNUTTlSS21pQmM' -O 'GoogleNews-vectors-negative300.bin.gz'
wget -c "https://s3.amazonaws.com/dl4j-distribution/GoogleNews-vectors-negative300.bin.gz"
rm cookies.txt
gunzip -f GoogleNews-vectors-negative300.bin.gz
