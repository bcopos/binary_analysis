#!/usr/bin/env python

'''
	From observations of CGC binary samples, side channels can be used to detect input size.
	The number of instructions executed (most of the time) changes when the input size is surpassed.
	Therefore, to find input size, we can look for two things:
	1) number of instructions executed changes once input size is surpassed
	2) the difference in number of instructions executed for string of size S and S+1 changes once input
	   size is surpassed

	FOR 2:
	More specifically, adding an additional character to an invalid input will result in X additional 
	instructions being executed. When the input string surpasses the expected input size (S), the 
	difference in the number of instructions between string of  size S and S+1 is different than that 
	between string of size S-1 and size S.
	Three of the following things have been observed:
		- # ins. drops: usually because program exits or segfaults
		- # ins. increases: function reading from stdin performs extra steps
		- # ins. stays the same: program exits but input fed to the program will "spill" onto terminal 
		  prompt (this is the trickiest but it also rarely happens, only 1 example DARPA CGC KPRCA3)
	
	Beware, sometimes program may exit prematurely (before reaching input size) because of a segfault. 
	There's not much we can do here. Nonetheless, we have determined the input size that will trigger a 
	segfault (we're still OK)
	
	Using these we can form a method for determining input size.
	First, check difference in # of inst. executed for small input size (i.e. "aa" and "aaa" and "aaaa").
	The third input is just to double check.
	Increase input size and see if delta is the same.
	If not, decrease in a binary search manner until limit is found.
	If not, increase exponentially.	

	SPECIAL CASE:
		delta oscilates between two values (CADET, palindrome)
		num of instr. never changes, program exits when input size > SIZE
		

	RETURN VALUES:
		0 - successful
		1 - two options:
			- something failed
			- if size is available, program crashes with 
			  inputs larger than specified size (could be a
			  segfault)


	DISCLAIMER: this is written as a proof of concept and some parts
		    are not very pretty and quite hacky...


'''

import string
import subprocess
import os
import time
import random
import sys
import argparse
import signal
import tempfile
import signal

from multiprocessing import Queue
from ..helpers import helpers

MIN_INPUT_SIZE=4
EPSILON=3
DEBUG=False

CHILD = None
BINARY = ""
PERF_FILE = ""
PERF = None

def init_perf(pid):	
	global PERF_FILE
	global PERF
	perfOut = tempfile.NamedTemporaryFile(delete=False)
	perfOut.close()
	PERF_FILE = perfOut.name
	PERF = helpers.attach_perf_nosample(pid, PERF_FILE)

def init_binary(binary):
	global BINARY
	global CHILD

	BINARY = binary

	CHILD = helpers.pexpect_spawn_process(BINARY)

	return CHILD

def restart_binary():
	global BINARY

	child = init_binary(BINARY)
	init_perf(child.pid)

	return child

def check_perfOutput(perfOut):
	f = open(perfOut, "r")
	lines = f.readlines()
	f.close()
	last_line = lines[-1:]
	for line in lines:
		if "instructions" in line:
			insCount = line.strip().split()[0]
			return int(insCount.replace(',',''))
	return 0

def find_size(binary, inputChar, delta1, delta2, num_inst, size, epsilon, perfFile, queue):
	if delta1 == 0 and delta2 == 0:
		# no change as input increases, increase until num_inst changes
		result = run_perf(CHILD, inputChar*(size+epsilon), perfFile)
		cur_num_ins = result['ins']
		exit = result['exit']
		backoff = (exit or num_inst not in range(cur_num_ins - 2, cur_num_ins + 2))
	elif delta1 > 0 and delta2 == 0:
		# linear increase (number of instructions) as input increases
		result1 = run_perf(CHILD, inputChar*size, perfFile)
		result2 = run_perf(CHILD, inputChar*(size+1), perfFile)
		diff = result2['ins'] - result1['ins']
		backoff = (result1['exit'] or result2['exit'] or diff not in range(delta1-2, delta1+2))	
	elif delta1 > 0 and delta2 > 0:
		# oscillation between two values as input increases
		result1 = run_perf(CHILD, inputChar*size, perfFile)
		result2 = run_perf(CHILD, inputChar*(size+1), perfFile)
		result3 = run_perf(CHILD, inputChar*(size+2), perfFile)
		diff1 = result2['ins'] - result1['ins']
		diff2 = result3['ins'] - result2['ins']
		backoff = (result1['exit'] or result2['exit'] or result3['exit'] or diff1 not in range(delta1-2,delta1+2) or diff2 not in range(delta2-2,delta2+2))	
	else:
		# all other cases, increase input until exit (if it happens)
		result = run_perf(CHILD, inputChar*size, perfFile)
		backoff = result['exit']

	# recursive call
	if backoff and epsilon != 1:
		epsilon = epsilon/2
		size = size - epsilon
		find_size(binary, inputChar, delta1, delta2, num_inst, size, epsilon, perfFile, queue)
	elif backoff and epsilon == 1:
		print "Size: " + str(size)
		queue.put(str(size))
		PERF.terminate(force=True)
		return 0
	elif not backoff and epsilon != 1:
		epsilon = epsilon*2
		size = size + epsilon
		find_size(binary, inputChar, delta1, delta2, num_inst, size, epsilon, perfFile, queue)
	elif not backoff and epsilon == 1:
		size = size + 1
		find_size(binary, inputChar, delta1, delta2, num_inst, size, epsilon, perfFile, queue)

'''
	Runs binary via PERF and extracts:
	1) number of instructions executed
	2) if segfault happened (showed up on stdout/stderr)
'''
def run_perf(child, inputStr, perfFile):
	global CHILD, PERF_FILE, PERF
	beforeRc, afterRc = helpers.pexpect_send_input(child, inputStr)
	PERF.terminate(force=True)
	time.sleep(0.2)
	ins = check_perfOutput(PERF_FILE)

	if DEBUG:
		print str(inputStr) + " " + str(beforeRc) + " " + str(afterRc) + " " + str(len(inputStr)) + " " + str(ins)
	
	CHILD = restart_binary()

	return {'ins': ins, 'exit': afterRc}

'''
	 Finds delta for short strings (2,3, and 4 chars)
	 Why not just 2 and 3 chars? Just to make sure it's not doing 
	 something weird (oscillating between even and odd length input or
	 other bizzarre things).
'''
def find_initial_delta(binary, inputChar, perfFile):
	r1 = run_perf(CHILD, inputChar*MIN_INPUT_SIZE, perfFile)
	r2 = run_perf(CHILD, inputChar*(MIN_INPUT_SIZE+1), perfFile)
	r3 = run_perf(CHILD, inputChar*(MIN_INPUT_SIZE+2), perfFile)
	r4 = run_perf(CHILD, inputChar*(MIN_INPUT_SIZE+3), perfFile)

	if r1 == 1 or r2 == 1 or r3 == 1 or r4 == 1:
		return 1

	delta1 = r2['ins'] - r1['ins']
	delta2 = r3['ins'] - r2['ins']
	delta3 = r4['ins'] - r3['ins']


	if delta1 not in range(delta2-2,delta2+2):
		if delta1 in range(delta3-2, delta3+2):
			return { 'delta1': delta1, 'delta2': delta2 }
		else:
			if DEBUG:
				print "PROBLEM: delta for small changes " + str(delta1) + " vs. " + str(delta2)
			sys.exit(1)
	elif delta1 == 0 or delta2 == 0:
		return { 'delta1': 0, 'delta2': 0 }

	return { 'delta1': delta1, 'delta2': 0 }

def find_input_length(binary, queue):
	inputChar = "a"

	child = init_binary(binary)
	init_perf(child.pid)

	result = find_initial_delta(child, inputChar, PERF_FILE)
	r = run_perf(CHILD, inputChar * MIN_INPUT_SIZE, PERF_FILE)
	if r['exit'] == 1:
		return 1
	find_size(child, inputChar, result['delta1'], result['delta2'], r['ins'], 1000, 1000, PERF_FILE, queue) 	
	PERF.terminate(force=True)


def main():	
	parser = argparse.ArgumentParser()
	parser.add_argument('-b','--binary', type=str, required=True, help="binary to be executed (with path)")
	parser.add_argument('-e','--expect', type=str, required=True, help="expect script (with path)")
	parser.add_argument('-o','--output', type=str, required=True, help="output file (with path)")

	args = parser.parse_args()
	
	global BINARY
	BINARY = args.binary
	expect = args.expect
	output = args.output

	queue = Queue()

	#find_input_length(binary, output, expect, queue)

if __name__ == "__main__":
	main()
