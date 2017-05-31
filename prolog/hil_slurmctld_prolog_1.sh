#!/bin/bash

/bin/echo "Hello, world, prolog here"
touch /tmp/foo

V=`lsof +f -ap $BASHPID -d 0,1,2 `
echo "$V" > /tmp/foo

exit 0

