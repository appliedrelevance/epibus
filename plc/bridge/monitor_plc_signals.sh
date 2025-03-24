#! /bin/bash

redis-cli -h 127.0.0.1 -p 6379 subscribe plc:signal_update plc:command