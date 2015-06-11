#!/usr/bin/env python

import os
import errno
import string
import tempfile
import time
import shutil
import signal

import utils
from ..helpers import helpers

'''
	TODO:
		- avoid strings made of same character repeating

		MAYBE:
		- restart binary after every command/argument found
'''
DEBUG = True

EPSILON = 4
P_CHARS = list(string.printable[:-6])

CHILD = None
BINARY = ""
PERF_FILE = ""
PERF_PID = None
CMDS = ""

DEMO_FILE = "/home/cgc/find_input.txt"

RESTART_AFTER_EVERY_CHAR = False

def init_perf(pid):	
	global PERF_FILE
	global PERF_PID
	perfOut = tempfile.NamedTemporaryFile(delete=False)
	perfOut.close()
	PERF_FILE = perfOut.name
	PERF_PID = helpers.attach_perf(pid, PERF_FILE)

def init_binary(binary):
	global BINARY
	BINARY = binary

	global CHILD
	CHILD = helpers.pexpect_spawn_process(BINARY)
	return CHILD

def send_initial_cmds(child, cmds):
	global CMDS
	if CMDS:
		# send these commands before finding input
		return helpers.pexpect_send_multiple_inputs(CHILD, cmds)

def find_input(binary, initial_cmds, queue, event):
	child = init_binary(binary)

	init_perf(child.pid)

	if initial_cmds:
		global CMDS
		CMDS = initial_cmds	
		send_initial_cmds(child, CMDS)

	find_valid_strings(child, "", PERF_FILE, [], queue)
	os.kill(PERF_PID, signal.SIGKILL)
	if event:
		event.set()

def find_args(binary, cmd, initial_cmds, queue):
	child = init_binary(binary)

	init_perf(child.pid)

	if initial_cmds:
		global CMDS
		CMDS = initial_cmds	

	cmd = cmd.strip()
	cmd += " "
	find_valid_strings(child, cmd, PERF_FILE, [], queue)
	os.kill(PERF_PID, signal.SIGKILL)

def find_valid_strings(child, cmd, perfFile, prev_validChars, queue):
	# try_chars
	validChars = try_chars(child, cmd, perfFile)

	# REMOVE THIS (only for a binary)
	if ':' in validChars:
		validChars.remove(':')
	
	# check for repeating characters
	try:
		if cmd[-1] in validChars and cmd[-2] in validChars and cmd[-1] == cmd[-2] and cmd[-1]:
			if queue:
				queue.put(cmd[:-1])
			else:
				print "CMD: " + str(cmd[:-1])
			return 0
	except IndexError:
		pass

	# base case
	if utils.check_base_case(validChars, prev_validChars) or len(validChars) == 0:
		if cmd:
			if queue:
				queue.put(cmd.strip())
			else:
				print "CMD: " + str(cmd)
				if DEBUG:
					print "NEW INPUT: ===>" + str(cmd) + "<===\n"
					#f = open(DEMO_FILE, 'a')
					#f.write("NEW INPUT: ===>" + str(cmd) + "<===\n")
					#f.flush()
					#f.close()	


		# restart binary after finding new argument (to start with clean slate)
		os.kill(PERF_PID, signal.SIGKILL)
		global CHILD
		if CHILD.isalive():
			CHILD.terminate(force=True)
		CHILD = restart_binary()

		return 0
	# all other cases
	else:
		# continue with the rest...
		for c in validChars:
			find_valid_strings(child, cmd + c, perfFile, validChars, queue)
		return 1
	
	return 0
	
def try_chars(child, inputStr, perfFile):
	if DEBUG:
		print "===============================================================\n"
		print "CMD: ===>" + str(inputStr) + "<===\n"
		#f = open(DEMO_FILE, 'a')
		#f.write("================================================================\n")
		#f.write("CMD:  ===>" + str(inputStr) + "<===\n")
		#f.flush()
		#f.close()
	scoreboard = generate_score_array()

	global CHILD
	c = ""
	for c in P_CHARS:
		ins = run_perf(CHILD, str(inputStr) + str(c), perfFile)
		scoreboard[c] = ins

		if DEBUG:
			print "char " + str(c) + " ins " + str(ins)

		if RESTART_AFTER_EVERY_CHAR:
			os.kill(PERF_PID, signal.SIGKILL)
			CHILD = restart_binary()

	freq = utils.find_freq(scoreboard)
	mode = utils.find_mode(freq)

	#if DEBUG:
	# 	print "SCOREBOARD1: " + str(scoreboard) + "\n"
	#scoreboard = check_scoreboard(scoreboard, mode)
	#if DEBUG:
	#	print "SCOREBOARD: " + str(scoreboard) + "\n"
		#f = open(DEMO_FILE, 'a')
		#f.write("SCOREBOARD: " + str(scoreboard) + "\n")
		#f.flush()
		#f.close()


	validInputs = utils.find_valid_all(scoreboard, EPSILON)
	validInputs = double_check_validChars(validInputs, inputStr, mode, EPSILON, perfFile)

	if DEBUG:
		#f = open(DEMO_FILE, 'a')
		#f.write("CHARS:" + str(validInputs) + "\n")
		#f.flush()
		#f.close()
		print "CHARS:" + str(validInputs)
	
	return validInputs

def double_check_validChars(validInputs, inputStr, mode, EPSILON, perfFile):
	global CHILD
	valid = list()
	for vc in validInputs:
		ins = run_perf(CHILD, inputStr+vc, perfFile)

		if RESTART_AFTER_EVERY_CHAR:
			os.kill(PERF_PID, signal.SIGKILL)
			CHILD = restart_binary()
		
		if ins not in range(mode-EPSILON,mode+EPSILON):
			valid.append(vc)
	return valid

def run_perf(child, inputStr, perfFile):
	beforeRc, afterRc = helpers.pexpect_send_input(child, inputStr)

	#if afterRc or not child.isalive():
		#if DEBUG:
		#	print "RESTARTED... " + str(inputStr) + " " + str(beforeRc) + " " + str(afterRc)
	#	global CHILD
	#	CHILD = restart_binary()

		# since input killed binary, return 0 (will still be an outlier)
	#	return 0

	ins = check_perfOutput(perfFile)
	return ins

###
#
# checks scoreboard for anomalies 
# 	e.g. constant rate of increase due to functions like strtoul
#
#	constant increase of ins between adjacent characters in a-f, A-F 
#		i.e. a = 10, b = 15, c = 20
#	
# 	fix: make all ins count for such characters equal to ins count of first char
#		i.e. a = 10, b = 10, c = 10
#
#
###
def check_scoreboard(sb, mode):
	alteredSb = {}
	curDelta = 0 
	prevDelta = 0
	index = 0
	pchars_len = len(P_CHARS)
	while index < pchars_len:
		try:
			firstCharIns = sb[P_CHARS[index]]
			nextCharIns = sb[P_CHARS[index+1]]
		except IndexError:
			break

		curDelta = int(nextCharIns - firstCharIns)

		if curDelta in range(prevDelta-EPSILON,prevDelta+EPSILON) and curDelta != 0:
			if index-1 < 0:
				alteredSb[P_CHARS[index]] = sb[P_CHARS[index]]
			else:	
				alteredSb[P_CHARS[index]] = alteredSb[P_CHARS[index-1]]
			alteredSb[P_CHARS[index+1]] = alteredSb[P_CHARS[index]]
		else:
			# guarantees a "fixed" entry doesn't get rewritten
			if not P_CHARS[index] in alteredSb.keys():
				alteredSb[P_CHARS[index]] = sb[P_CHARS[index]]
			alteredSb[P_CHARS[index+1]] = sb[P_CHARS[index+1]]


		prevDelta = curDelta	

		index += 1
	
	alteredSb[P_CHARS[index]] = sb[P_CHARS[index]]	

	return alteredSb

def check_perfOutput(perfOut):
	#time.sleep(0.05)
	f = open(perfOut, "r")
	lines = f.readlines()
	f.close()
	lastLine = lines[-1:]
	if not lastLine:
		#print "error1"
		#print lines
		return 1
	else:
		lastLine = lastLine[0]
	if not "instructions" in lastLine:
		#print "error2"
		return 1

	ins_count = lastLine.strip().split()[1]
	return int(ins_count.replace(',',''))


def generate_score_array():
	scoreboard = dict(zip(P_CHARS, [0 for i in P_CHARS]))
	return scoreboard

def restart_binary():
	global BINARY
	global PERF_FILE
	global PERF_PID

	os.kill(PERF_PID, signal.SIGKILL)

	child = init_binary(BINARY)
	PERF_PID = helpers.attach_perf(child.pid, PERF_FILE)

	if CMDS:
		send_initial_cmds(child, CMDS)		

	return child

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-b','--binary', type=str, required=True, help="binary to be executed (with path)")
	args = parser.parse_args()
	binary = args.binary

	queue = ""
	find_input(binary, "", queue, "")

if __name__ == '__main__':
	main()

#################################################################################


# TODO: avoid endless strings composed of same character
	#try:
	#	if cmd[-1:] in validChars and cmd[-2] in validChars:
	#		print "ENDLESS"
	#		validChars.remove(cmd[-1:])
	#except IndexError:
	#	pass	
