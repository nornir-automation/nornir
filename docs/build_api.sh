#!/bin/sh
DST=docs/api/

rm -rf $DST/nornir

for f in `find nornir -name "*.py"`; do
    DIR=$DST/`dirname $f`
    FILE=$DST/`echo $f | sed "s/\.py$/.rst/"`
    IMPORT=`echo $f | sed "s/\.py$//" | sed "s/\//./g"`
    mkdir -p $DIR
    cat <<EOF > $FILE
$IMPORT
=========================================

.. automodule:: $IMPORT
  :members:
  :undoc-members:
EOF
done
