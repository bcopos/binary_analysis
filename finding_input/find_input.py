#!/usr/bin/env python

'''
	This script aims at finding valid inputs for binaries by looking at the number 
	of instructions executed for each printable character at every index (starting 
	with 0).

	Specifically:
		1. Start with empty string
		2. Use a concatentation of the string and one character (at a time) from
		   the list of printable characters
		3. Run binary while measuring number of instructions (we use perf here
		   but GDB also works, just slower) with the input from above (2)
		4. Measure the mode number of instructions across all runs
		5. The characters with number of instructions OUTSIDE the range of 
		   mode +/- epsilon
		6. Double check characters from (5) by re-running the binary with a
		   concatenation of string and character as input. (we do this to account 
		   for hardware counting mess-ups)
		7. Use the results from (6) to move on to the next index. Use characters
		   from previous index to determine valid characters for current index.
		   If we were to visualize this process, it resembles a tree structure
		   with characters at nodes where a pre-order traversal results in the 
		   strings we have constructed. During the traversal, every time a leaf
		   is reached, we have reached the end of a valid input string.

	Components:
		run_perf()           - runs the binary with perf to count inst.
		find_mode()          - finds the mode for the inst. count across all 
			 	       printable characters at that index
		find_valid_chars()   - looks for characters with # of inst. outside
				       the range of mode +/- EPSILON (to account for
				       imperfections in hardware counters)
		double_check_chars() - once we found possible valid chars, re-run using 
				       those characters to make sure the hardware 
				       counters weren't hiccuping


'''


import string
import subprocess
import os
import time
import random
import pexpect
import math
import numpy

from multiprocessing import Process, Queue

# MODE num of instructions +/- EPSILON to find possible valid characters for index
EPSILON = 5
DEBUG = True
P_CHARS = [c for c in string.printable[:-6]]
NUMERIC_CHARS = [c for c in P_CHARS[0:10]]
ALPHABETIC_CHARS = [c for c in P_CHARS[10:63]]
SPECIAL_CHARS = [c for c in P_CHARS[63:]]

valid_chars_per_index = {}
processes = []
strings = []

def find_input_type(string):
	numeric = False
	alphabetic = False
	special = False
	for c in NUMERIC_CHARS:
		if c in string:
			numeric = True
			break
	for c in ALPHABETIC_CHARS:
		if c in string:
			alphabetic = True
			break
	for c in SPECIAL_CHARS:
		if c in string:
			special = True
			break
	if alphabetic and not numeric and not special:
		return "alphabetic"
	elif not alphabetic and numeric and not special:
		return "numeric"
	elif not alphabetic and not numeric and special:
		return "special"
	elif alphabetic and numeric and not special:
		return "alphanumeric"
	elif alphabetic and not numeric and special:
		return "alphabetic with special chars"
	elif alphabetic and numeric and special:
		return "alphanumeric with special chars"
	else:
		return "not sure"
 
	

#runs perf with a given string as a parameter
def run_perf(string):
	out, err = subprocess.Popen(["../expect_input", string], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
#	print out
	lines = out.split(os.linesep)
	for line in lines:
		if "instructions:u" in line and "stat" not in line:
			line = line.strip()
			ins, txt = line.split()
			return int(ins.replace(',',''))
	return 0

'''
	To find valid input:
		- get mode of the list of values (most frequent = most likely incorrect char)
		- get keys which have values other than the mode (+- some wiggle room value)
		- use those keys(/characters) to find next character and continue
'''
def find_valid_chars(scoreboard, mode, epsilon):
	input_chars = list()
	r = range(mode-epsilon,mode+epsilon)
	for k,v in scoreboard.iteritems():
		if v not in r and v != 0:
			# v != SHOULDN'T HAPPEN! it means perf execution failed... this is just a hack
			input_chars.append(k)
	return input_chars

def find_freq(scoreboard):
	freq = {}
	for v in scoreboard.values():
		try:
			freq[v] += 1
		except  KeyError:
			freq[v] = 1
	return freq

def find_mode(freq):
	maxKey = max(freq, key=freq.get)
#	if DEBUG:
#		print "FREQ: " + str(freq)
#		print "MODE: " + str(maxKey)
	return maxKey

def generate_score_array():
	scoreboard = dict(zip(P_CHARS, [0 for i in P_CHARS]))
	return scoreboard

def double_check_chars(string, chars, mode, epsilon):
	final_chars = []
	for c in chars:
		score = run_perf(str(string) + str(c))
		if score not in range(mode-epsilon, mode+epsilon):
			final_chars.append(c)
	return final_chars

def get_first_char(index):
	scoreboard = generate_score_array()
	for c in P_CHARS:
		scoreboard[c] = run_perf(c)

	freq = find_freq(scoreboard)
	mode = find_mode(freq)

	valid_char = find_valid_chars(scoreboard, mode, EPSILON)
#	print "VALID_INPUTS 1: " + str(valid_char)
	if len(valid_char) != 1:
		valid_char = double_check_chars("", valid_char, mode, EPSILON)
#		print "VALID_INPUTS 2: " + str(valid_char)

	valid_chars_per_index[index] = valid_char
	#print "INDEX: " + str(index) + "\nSCOREBOARD: " + str(scoreboard)
	print "\nVALID_CHARS: " + str(valid_chars_per_index)
	return mode

def try_chars(s, index, valid_chars_per_index):
	scoreboard = generate_score_array()
	c = ""
	for c in P_CHARS:
		scoreboard[c] = run_perf(str(s) + str(c)) 

	freq = find_freq(scoreboard)
	mode = find_mode(freq)

	# find valid characters (anything outside range of mode+/-EPSILON)
	valid_inputs = find_valid_chars(scoreboard, mode, EPSILON)
#	print "VALID_INPUTS 1: " + str(valid_inputs)

	# double check (to make sure hardware counter didn't mess up)
	valid_inputs = double_check_chars(s, valid_inputs, mode, EPSILON)
#	print "VALID_INPUTS 2: " + str(valid_inputs)

	# if no characters are valid, we reached end of a input string
	if len(valid_inputs) == 0:
		#write to file (obtain lock if in parallel)
		strings.append(s)
		out = open("strings.txt", 'a')
		out.write(s+" "+str(find_input_type(s))+"\n")
		out.close()

	valid_chars_per_index[index] = valid_inputs

	if DEBUG:
		#print "INDEX: " + str(index) + "=" + str(s) + "=\nSCOREBOARD: " + str(scoreboard)
		print "\nVALID_CHARS: " + str(valid_chars_per_index)
	for c in valid_chars_per_index[index]:
		try_chars(str(s) + str(c), index+1, valid_chars_per_index)

if __name__ == '__main__':
	processes = []
	scoreboard = generate_score_array()
	index = 0

	mode = get_first_char(index)
	for c in valid_chars_per_index[index]:
		index = 1
		try_chars(c, index, dict())
	
	# try to find arguments
	#index = 0
	#for s in strings:
	#	try_chars(s+" ", index, dict())

	print "DONE"
	out = open("strings.txt", 'a')
	out.write("DONE\n")
	out.close()

