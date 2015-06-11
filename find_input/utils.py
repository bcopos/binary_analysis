#!/usr/bin/env python

from subprocess import Popen

import os
import string
import random
import tempfile
import pexpect
import string
import time

P_CHARS = list(string.printable[:-6])
ALPHABETIC_CHARS = [c for c in P_CHARS[10:63]]
UPPER_ALPHABETIC_CHARS = [c for c in ALPHABETIC_CHARS[26:]]
LOWER_ALPHABETIC_CHARS = [c for c in ALPHABETIC_CHARS[:26]]
LOWER_AF_CHARS = LOWER_ALPHABETIC_CHARS[0:6]
UPPER_AF_CHARS = UPPER_ALPHABETIC_CHARS[0:6]

SPECIAL_CHARS = [c for c in P_CHARS[63:]]
NUMERIC_CHARS = [c for c in P_CHARS[0:10]]

PIN = "/home/cgc/pin/pin"
PIN_TOOL = "/home/cgc/pin/source/tools/BasicBlockCoverage/obj-ia32/pin-code-coverage-cgc.so"

# this accounts for when the number of valid input digits 0-10 is more than non-valid input digits
# e.g. 0-8 are valid, 9-10 non-valid, here the mode num of ins represents valid chars
def find_valid_nums2(scoreboard, epsilon):
	modeAll = find_mode(find_freq(scoreboard))
	
	numScoreboard = {}
	for n in NUMERIC_CHARS:
		numScoreboard[n] = scoreboard[n]

	return find_valid_chars(numScoreboard, modeAll, epsilon)

def find_valid_nums(scoreboard, epsilon):
	numScoreboard = {}
	for n in NUMERIC_CHARS:
		numScoreboard[n] = scoreboard[n]

	return find_valid_chars(numScoreboard, find_mode(find_freq(numScoreboard)), epsilon)

def find_valid_af(scoreboard, epsilon):
	afScoreboard = {}
	for n in LOWER_AF_CHARS:
		afScoreboard[n] = scoreboard[n]

	return find_valid_chars(afScoreboard, find_mode(find_freq(afScoreboard)), epsilon)

def find_valid_AF(scoreboard, epsilon):
	AFScoreboard = {}
	for n in UPPER_AF_CHARS:
		AFScoreboard[n] = scoreboard[n]

	return find_valid_chars(AFScoreboard, find_mode(find_freq(AFScoreboard)), epsilon)

def find_valid_az(scoreboard, epsilon):
	azScoreboard = {}
	for n in LOWER_ALPHABETIC_CHARS:
		azScoreboard[n] = scoreboard[n]

	return find_valid_chars(azScoreboard, find_mode(find_freq(azScoreboard)), epsilon)

def find_valid_AZ(scoreboard, epsilon):
	AZScoreboard = {}
	for n in UPPER_ALPHABETIC_CHARS:
		AZScoreboard[n] = scoreboard[n]

	return find_valid_chars(AZScoreboard, find_mode(find_freq(AZScoreboard)), epsilon)

def find_valid_special(scoreboard, epsilon):
	s = {}
	for n in SPECIAL_CHARS:
		s[n] = scoreboard[n]

	return find_valid_chars(s, find_mode(find_freq(s)), epsilon)

def find_valid_printable(scoreboard, epsilon):
	return find_valid_chars(scoreboard, find_mode(find_freq(scoreboard)), epsilon)

def find_valid_chars(scoreboard, mode, epsilon):
	input_chars = list()
	r = range(mode-epsilon,mode+epsilon)
	for k,v in scoreboard.iteritems():
		if v not in r:
			input_chars.append(k)
	
	return input_chars

def find_valid_all(scoreboard, epsilon):
	num = find_valid_nums(scoreboard, epsilon) 
	af_l = find_valid_af(scoreboard, epsilon)
	af_u = find_valid_AF(scoreboard, epsilon)
	az_l = find_valid_az(scoreboard, epsilon)
	az_u = find_valid_AZ(scoreboard, epsilon)
	pchars = find_valid_printable(scoreboard, epsilon)
	special = find_valid_special(scoreboard, epsilon)


#	print num
#	print af_l
#	print af_u
#	print az_l
#	print az_u
#	print pchars

	# if binary only accepts a-f or A-F (for some odd reason)
	if (set(LOWER_AF_CHARS).issubset(az_l)):
		lower = list(set(af_l) & set(az_l))
	else:
		lower = list(set(af_l).union(set(az_l)))

	if (set(UPPER_AF_CHARS).issubset(az_u)):
		upper = list(set(af_u) & (set(az_u)))
	else:
		upper = list(set(af_u).union(set(az_u)))

#	if not (set(num).issubset(pchars)) or set(NUMERIC_CHARS).issubset(pchars):
#		nums = find_valid_nums2(scoreboard, epsilon)
#	else:
#		nums = list(set(num) & set(pchars))

	valid_chars = list(set(pchars) & set(lower)) + list(set(pchars) & set(upper)) + list(set(pchars) & set(special)) + list(set(pchars) & set(num))

	# the only time this doesn't work is if all chars in any set (UPPER_ALPH, NUMS, SPECIAL)
	# are valid chars
#	if set(UPPER_ALPHABETIC_CHARS).issubset(set(pchars)) and len(az_u) == 0:
#		valid_chars += UPPER_ALPHABETIC_CHARS
#	if set(LOWER_ALPHABETIC_CHARS).issubset(set(pchars)) and len(az_l) == 0:
#		valid_chars += LOWER_ALPHABETIC_CHARS
#	if set(NUMERIC_CHARS).issubset(set(pchars)) and len(num) == 0:
#		valid_chars += NUMERIC_CHARS
#	if set(SPECIAL_CHARS).issubset(set(pchars)) and len(special) == 0:
#		valid_chars += SPECIAL_CHARS
	# ignore cases where af and AF are valid chars but nothing else
	# why? catch 22, it won't cover other corner cases such as KPRCA1 and the strtoul problem
	#if set(LOWER_AF_CHARS).issubset(set(pchars)) and len(af_l) == 0:
	#	valid_chars += LOWER_AF_CHARS
	#if set(UPPER_AF_CHARS).issubset(set(pchars)) and len(af_u) == 0:
	#	valid_chars += UPPER_AF_CHARS

	return valid_chars


###
#
# Finds frequency of values in a dictionary (used to then compute mean)
#
# Scoreboard = { 'a': 1, 'b': 2 ... }
# 
###
def find_freq(scoreboard):
	freq = {}
	for v in scoreboard.values():
		try:
			freq[v] += 1
		except KeyError:
			freq[v] = 1
	return freq

###
#
# Given a dictionary of values and their number of occurance, computes mode
#
###
def find_mode(freq):
	maxKey = max(freq, key=freq.get)
	#print "FREQ: " + str(freq)
	#print "MODE: " + str(maxKey)
	return maxKey

def check_base_case(validChars, prevValidChars):
	# check if valid chars are the same as last index
#	if valid_chars == prev_valid_chars:
#		return True

	# check if valid chars are either: all printable chars, all numbers, all caps, all lowercase
	# (i.e. no special input detected)
	inputCharsSet = set(validChars)
	if inputCharsSet == set(P_CHARS):
		return True
	if inputCharsSet == set(ALPHABETIC_CHARS):
		return True
	if inputCharsSet == set(UPPER_ALPHABETIC_CHARS):
		return True
	if inputCharsSet == set(LOWER_ALPHABETIC_CHARS):
		return True
	if inputCharsSet == set(NUMERIC_CHARS):
		return True
	return False

def log(logfile, msg):
	f = open(logfile, "a")
	f.write(msg + "\n")
	f.close()
'''
###
#
# Used to send strings to a binary via expect
#
###
def send_string(event, binary, input_string, expect, input_files_dir, output_files_dir, segfault_files_dir, logfile):
	child = Popen([expect, input_string, binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out = child.communicate()[0]
	returncode = child.returncode

	filename = ''.join(random.choice(string.ascii_uppercase) for i in range(12))

	segfault = True
	if returncode != 0 and not "fault" in out:
		segfault = False	
		log(logfile, "Sending input failed")
		return 1

	if not "fault" in out:
		segfault = False

	if segfault:
		in_file = segfault_files_dir + "/" + filename + ".input"
		out_file = segfault_files_dir + "/" + filename + ".output"
		log(logfile, "Found segfault")
		# process output to eliminate perf output and segmentation fault error
		proc_out = out.split()[:-14]
	else:
		in_file = input_files_dir + "/" + filename
		out_file = output_files_dir + "/" + filename
		# process output to eliminate perf output
		proc_out = out.split()[:-11]

	i = open(in_file, "w")
	i.write(input_string)
	i.close()
		
	o = open(out_file, "w")
	o.write(' '.join(proc_out))
	o.close()

	event.set()
	return 0
'''
