#!/usr/bin/env python

from subprocess import Popen

import os
import string
import random
import tempfile
import pexpect
import string
import time

P_CHARS = [c for c in string.printable[:-6]]
ALPHABETIC_CHARS = [c for c in P_CHARS[10:63]]
UPPER_ALPHABETIC_CHARS = [c for c in ALPHABETIC_CHARS[26:]]
LOWER_ALPHABETIC_CHARS = [c for c in ALPHABETIC_CHARS[:26]]
LOWER_AF_CHARS = LOWER_ALPHABETIC_CHARS[0:6]
UPPER_AF_CHARS = UPPER_ALPHABETIC_CHARS[0:6]

SPECIAL_CHARS = [c for c in P_CHARS[63:]]
NUMERIC_CHARS = [c for c in P_CHARS[0:10]]

PIN = "/home/cgc/pin/pin"
PIN_TOOL = "/home/cgc/pin/source/tools/BasicBlockCoverage/obj-ia32/pin-code-coverage-cgc.so"

def spawn_process(binary):
	return Popen(binary.split()).pid

def pexpect_spawn_process(binary):
	child = pexpect.spawn(binary)
	child.delaybeforesend = 0.2
	return child

def pexpect_spawn_process_pin(binary, trace_file):
 	pinCmd = PIN + " -t " + PIN_TOOL + " -o " + trace_file + " -- " + binary
	child = pexpect.spawn(pinCmd)
	child.delaybeforesend = 0.3
	return child
	
####
#
# Checks if child is alive, sends input, checks if child is alive post input
#
# Returns tuple:
#	(before_input_status, after_input_status)
#
####
def pexpect_send_input(child, input_str):
	if not child.isalive():
		if child.exitstatus != None:
			return child.exitstatus, 0
		else:
			return child.signalstatus, 0
	child.sendline(input_str)
	time.sleep(0.3)
	if not child.isalive():
		if child.exitstatus != None:
			return 0, child.exitstatus
		else:
			return 0, child.signalstatus
	return 0, 0

def pexpect_send_input_check_exit(child, input_str):
	if not child.isalive():
		if child.exitstatus != None:
			return child.exitstatus
		else:
			return child.signalstatus
	child.sendline(input_str)
	time.sleep(2)
	if not child.isalive():
		return 1
	return 0

def pexpect_send_multiple_inputs(child, inputs):
	for i in inputs:
		beforeRc, afterRc = pexpect_send_input(child, i)
		if beforeRc:
			return beforeRc
		if afterRc:
			return afterRc
	if not child.isalive():
		return 1
	return 0

def pexpect_spawn_and_send(binary, input_str):
	child = pexpect_spawn_process(binary)
	return pexpect_send_input(child, input_str)

def pexpect_kill_process(child):
	if child.isalive():
		child.terminate(force=True)

	if child.exitstatus != None:
		return child.exitstatus
	else:
		return child.signalstatus

def attach_pin(pid, trace_file):
 	pinCmd = PIN + " -pid " + str(pid) + " -t " + PIN_TOOL + " -o " + trace_file
	print pinCmd
	return spawn_process(pinCmd)

def attach_perf(pid, perf_file):
	perf_cmd = "perf stat -e instructions:u -I 100 -o " + perf_file + " -p " + str(pid)
	return spawn_process(perf_cmd)

def attach_perf_nosample(pid, perf_file):
	perf_cmd = "perf stat -e instructions:u -o " + perf_file + " -p " + str(pid)
	return pexpect_spawn_process(perf_cmd)

def find_valid_nums(scoreboard, epsilon):
	numScoreboard = {}
	for n in NUMERIC_CHARS:
		numScoreboard[n] = scoreboard[n]

	return find_valid_chars(numScoreboard, find_mode(find_freq(numScoreboard)), epsilon)

def find_valid_af(scoreboard, epsilon):
	af_scoreboard = {}
	for n in LOWER_AF_CHARS:
		af_scoreboard[n] = scoreboard[n]

	return find_valid_chars(af_scoreboard, find_mode(find_freq(af_scoreboard)), epsilon)

def find_valid_AF(scoreboard, epsilon):
	AF_scoreboard = {}
	for n in UPPER_AF_CHARS:
		AF_scoreboard[n] = scoreboard[n]

	return find_valid_chars(AF_scoreboard, find_mode(find_freq(AF_scoreboard)), epsilon)

def find_valid_az(scoreboard, epsilon):
	az_scoreboard = {}
	for n in LOWER_ALPHABETIC_CHARS:
		az_scoreboard[n] = scoreboard[n]

	return find_valid_chars(az_scoreboard, find_mode(find_freq(az_scoreboard)), epsilon)

def find_valid_AZ(scoreboard, epsilon):
	AZ_scoreboard = {}
	for n in UPPER_ALPHABETIC_CHARS:
		AZ_scoreboard[n] = scoreboard[n]

	return find_valid_chars(AZ_scoreboard, find_mode(find_freq(AZ_scoreboard)), epsilon)

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

	print num
	print af_l
	print af_u
	print az_l
	print az_u
	print pchars

	lower = list(set(af_l) & set(az_l))
	upper = list(set(af_u) & set(af_u))
	valid_chars = list(set(pchars) & set(lower)) + list(set(pchars) & set(upper)) + list(set(pchars) & set(num)) + list(set(pchars) & set(special))

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

def log(logfile, msg):
	f = open(logfile, "a")
	f.write(msg + "\n")
	f.close()

def clean_file(filename):
	f = open(filename, "w")
	f.write("")
	f.close()
