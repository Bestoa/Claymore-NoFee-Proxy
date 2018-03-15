# Claymore-NoFee-Proxy

## What's this? How it works?

## Why do you rewrite this tool?
1. It was wrote with python 2.7.
2. If someone connect to the proxy, but do nothing and close the socket, it may add one thread permanently.
3. It will cause CPU usage becomes very high.

## Setup

### Python
Python 3 is required

## RUN
Run the proxy daemon first and pay attention to change the pool you use, you must specify here your real pool (here mininghub.ltd):
```
./stratum_proxy.py 8008 eth-eu2.mininghub.ltd 9999 0xB7716d5A768Bc0d5bc5c216cF2d85023a697D04D
```
