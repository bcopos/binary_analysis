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
	segfault (we're still OK bro)
	
	Using these we can form a method for determining input size.
	First, check difference in # of inst. executed for small input size (i.e. "aa" and "aaa" and "aaaa").
	The third input is just to double check.
	Increase input size and see if delta is the same.
	If not, decrease in a binary search manner until limit is found.
	If not, increase exponentially.	

	SPECIAL CASE:
		delta oscilates between two values (CADET, palindrome)
		num of instr. never changes, program exits when input size > SIZE
		
'''

import string
import subprocess
import os
import time
import random
import sys

MIN_INPUT_SIZE = 2
EPSILON=3
PROMPT=":~$"

'''
	Runs binary via PERF and extracts:
	1) number of instructions executed
	2) if segfault happened (showed up on stdout/stderr)
'''
def run_perf(string):
	out, err = subprocess.Popen(["./expect_input", string], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
#	print out
	exit = False
	lines = out.split(os.linesep)
	text_after_prompt = (lines[-1].split("$"))[-1]
	line_num = 0
	for line in lines:
		if "instructions:u" in line and "stat" not in line:
			# find first prompt line after perf output
			prompt_line = lines[line_num+4]
			
			# check if binary segfaulted
			if "Segmentation fault" in out:
				exit = True

			# check if input spilled onto prompt line after perf output
			if PROMPT in prompt_line_after_perf_output:
				text_after_prompt = (prompt_line.split("$"))[-1]
				if string[0] in text_after_prompt:
					exit = True

			# extract perf output
			line = line.strip()
			ins, txt = line.split()
			return {'ins':int(ins.replace(',','')), 'exit':exit}
		line_num += 1
	return {'ins':0, 'exit': exit}


'''
	Ahh the heart of this whole thing... mostly. Explanation is at the top of this file.
	Essentially looks for differences in the delta of longer input and shorter input
	as the size of the input grows. The size of the input grows in a binary search-like
	manner to allow for quicker "convergence" on where the difference first occurs.
'''
def find_limit(input_char, delta, size, epsilon):
	print "=========="
	print "DELTA: " + str(delta) + " SIZE: " + str(size) + " EPS: " + str(epsilon)
	if epsilon == 1:
		print size-1
		return "epsilon is 1"

	r1 = run_perf(input_char*size)
	r2 = run_perf(input_char*(size+1))
	shorter_input_ins = r1['ins']
	longer_input_ins = r2['ins']

	if r1['exit'] or r2['exit']:
		find_exit(input_char, size, size/2)
		return 0


	if shorter_input_ins == 0:
		r1 = double_check(input_char,size)
	if longer_input_ins == 0:
		r2 = double_check(input_char,size)


	if shorter_input_ins == 0 or longer_input_ins == 0:
		print "# INS should never be 0"
		sys.exit(1)

	new_delta = longer_input_ins - shorter_input_ins
	print "R1: " + str(shorter_input_ins)
	print "R2: " + str(longer_input_ins)
	print "D: " + str(new_delta)

	# If not in range, double check	
	if new_delta not in range(delta-2,delta+2):
		r1 = run_perf(input_char*size)
		r2 = run_perf(input_char*(size+1))
		shorter_input_ins = r1['ins']
		longer_input_ins = r2['ins']
		new_delta = longer_input_ins - shorter_input_ins

	# if really not in range, act accordingly
	if new_delta not in range(delta-2,delta+2):
		print "NOT IN RANGE"
		epsilon = epsilon/2
		find_limit(input_char, delta, size - epsilon, epsilon)
	else:
		print "IN RANGE"
		epsilon = epsilon*2
		find_limit(input_char, delta, size + epsilon, epsilon)


'''
	 Finds delta for short strings (2,3, and 4 chars)
	 Why not just 2 and 3 chars? Just to make sure it's not doing 
	 something weird (oscillating between even and odd length input or
	 other bizzarre things).
'''
def find_delta_short(input_char):
	r1 = run_perf(input_char*MIN_INPUT_SIZE)
	r2 = run_perf(input_char*(MIN_INPUT_SIZE+1))
	r3 = run_perf(input_char*(MIN_INPUT_SIZE+2))
	r4 = run_perf(input_char*(MIN_INPUT_SIZE+3))

	if detect_oscillations(r1, r2, r3, r4):
		find_limit_oscillations_case(input_char, diff1, diff2, size, size/2)

	shorter_input_ins = r1['ins']
	longer_input_ins = r2['ins']
	even_longer_input_ins = r3['ins']

	delta1 = longer_input_ins - shorter_input_ins
	delta2 = even_longer_input_ins - longer_input_ins

	if delta1 not in range(delta2-2,delta2+2):
		print "PROBLEM: delta for small changes " + str(delta1) + " vs. " + str(delta2)
		sys.exit(1)
	if delta1 == 0 or delta2 == 0:
		return 0
	return delta1


'''
	If delta is zero, increase input until change in the number of 
	instructions executed, segfault or exit.
'''
def zero_delta(input_char, num_ins, size, epsilon):
	r = run_perf(input_char*(size+epsilon))
	cur_num_ins = r['ins']
	exit = r['exit']
	if exit:
		find_exit(input_char, size, size/2)
		return 0

	if epsilon == 1:
		print size
		return 0

	if cur_num_ins in range(num_ins-2,num_ins+2):
		epsilon = epsilon*2
		zero_delta(input_char, num_ins, size + epsilon, epsilon)
	else:
		epsilon = epsilon/2
		zero_delta(input_char, num_ins, size - epsilon, epsilon)


	
'''
	If when running a binary with an input, the binary exits because of:
	1) segfault
	2) program logic (exits when input is too large, causing leftover bytes
	   to pop up on terminal prompt after program's exit)

	Then stop any other approach and find first instance of the event (whichever
	one of the two listed happens)

	Since this function gets called at the first instance of the event, we've 
	already surpassed the maximum input size that will cause the event, therefore
	we just decrease the size of the input to find where the event first occurs
	(at what size)

	tl;dr; decrease in size until first instance is reached, no point in increasing
'''
def find_exit(input_char, size, epsilon):
	if epsilon <= 1:
		print size
		return 0
	r = run_perf(input_char*size)	
	print "find_exit() size: " + str(size) + " epsilon " + str(epsilon)
	if r['exit']:
		print "found another exit"
		size = size - epsilon
		find_exit(input_char, size, epsilon/2)
	else:
		print "found no other segfault"
		size = size + epsilon
		find_exit(input_char, size, epsilon/2)



'''
	Detects if program does weird stuff depending on even/odd sized input
	Look for consistent oscillations 
'''
def detect_oscillations(r1,r2,r3,r4):
	if r1['ins'] in range(r3['ins']-1,r3['ins']+1) and r2['ins'] in range(r4['ins']-1,r4['ins']+1):
		return True
	return False

'''
	Increments input size by 1.
	This function is just for testing to observe behavior
'''
def test(input_char):
	count = 1
	while (count < 1000):
		r1 = run_perf(input_char*count)
		time.sleep(0.5)
		count = count+1
		r2 = run_perf(input_char*count)
		new_delta = r2 - r1
		print "R"+str(count-1)+": " + str(r1) + " R"+str(count)+": " + str(r2) + " D: " + str(new_delta)


if __name__ == '__main__':
	#test("a")
	input_char = "a"	
	delta = find_delta_short(input_char)
	if delta == 0:
		r = run_perf(input_char*MIN_INPUT_SIZE)
		zero_delta(input_char, r['ins'], 1000, 1000)
	else:
		find_limit(input_char, delta, 1000, 1000)
	#print delta
