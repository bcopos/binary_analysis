#!/usr/bin/env python

'''
	Given a set of commands:
	1. compute permutations of length L
	2. for each permutation
	3. send ith command
		- try to find args
			- once args found, move on to next cmd
		- save trace 
	4. once done with all permutations of length L
		- compare traces pertaining to the same string at the same index of the input strings
			- detect any "exit"-like commands
	5. move on to permutations of length L+1
			- if order determine for L
				- keep the same order?
'''


import itertools
import tempfile
import shutil
import subprocess
import os
import time

from multiprocessing import Process, Queue
from threading import Thread

from ..find_input import find_input
from ..helpers import helpers
import utils

CGC2ELF = "/home/cgc/cgc2elf/cgc2elf"
CMDARGS = dict()

def compute_cmd_perms(cmds):
	permutations = dict()
	for i in range(2, 5):
		permutations[i] = list(itertools.permutations(cmds, r=i))
	return permutations 

def main(binary, cmds):
	permutations = compute_cmd_perms(cmds)

	# for each size of cmd permutations
	for length in permutations.keys():
		print "Starting length " + str(length)
		pool = []
		##results = Queue()
		results = []
		for p in permutations[length]:
			print "Starting permutation of length " + str(length) + ": " + str(p)
			execute_cmds(binary, list(p), 0, results)
			##trace_process = Process(target=execute_cmds, args=(binary, list(p), 0, results))
			##trace_process.start()
			##pool.append(trace_process)
	
		collect_traces(binary, pool, results)	
		# start thread that waits for results and compares cfgs
		##t = Thread(target=collect_traces, args=(list(pool), results))
		##t.start()
		##collect_traces(pool, results)	

def execute_cmds(binary, cmds, index, queue):
	print "cmds: " + str(cmds) + " index: " + str(index)
	# base case
	if index == len(cmds):	
		# execute "processed" binary (for PIN purposes) and attach pin
		pinBinary = prepare_pin_binary(binary)
		pinTraceFile = tempfile.NamedTemporaryFile(delete=False)
		pinTraceFile.close()
		child = helpers.pexpect_spawn_process_pin(pinBinary, pinTraceFile.name)
		##pinPid = helpers.attach_pin(child.pid, pinTraceFile.name)
		rc = helpers.pexpect_send_multiple_inputs(child, cmds)

		if rc:
			print "binary died at some point (could be good -- 'exit'-like cmd -- or bad)"

		if child.isalive():
			child.terminate(force=True)
		##os.kill(pinPid, 0)

		# remove binary used for pin
		os.remove(pinBinary)

		# save trace
		print "inputs: " + str(cmds) + " " + str(pinTraceFile.name)
		print "DONE"
		##queue.put({"inputs": cmds, "trace": pinTraceFile.name})
		queue.append({"inputs": list(cmds), "trace": pinTraceFile.name})
		return 0

	# code from here to end of function tries to find arguments

	# find initial commands
	initCmds = cmds[0:-index]
	# find_args for current command
	lastCmd = cmds[index]

	print "init_cmds: " + str(initCmds)
	print "last_cmd: " + str(lastCmd)

	global CMDARGS
	try:
		i = CMDARGS[index].keys()
	except KeyError:
		CMDARGS[index] = dict()

	if lastCmd in CMDARGS[index].keys():
		for arg in CMDARGS[index][lastCmd]:
			cmds[index] = arg.strip()
			execute_cmds(binary, cmds, index+1, queue)
	else:
		args = Queue()
		find_input.find_args(binary, last_cmd, init_cmds, args)
		while not args.empty():
			arg = args.get()
			print "ARG: " + str(arg)
			cmds[index] = arg.strip()
			try:
				CMDARGS[index][lastCmd].append(arg)
			except KeyError:
				CMDARGS[index][lastCmd] = [ arg ]
			execute_cmds(binary, list(cmds), index+1, queue)

	return 0

'''
	For CGC binaries, PIN doesn't work directly on them
	First, it must be converted to elf format (cgc2elf tool)
'''
def prepare_pin_binary(binary):
	pinBinary = tempfile.NamedTemporaryFile(delete=False)
	pinBinary.close()

	# copy original binary
	shutil.copy(binary, pinBinary.name)

	# use cgc2elf to convert cgc bin to elf format
	cmd = CGC2ELF + " " + pinBinary.name
	print cmd
	err = subprocess.call([CGC2ELF, pinBinary.name])
	if err:
		print "cgc2elf failed"

	return pinBinary.name

'''
	Compares executions with input of same length (same num of cmds)
'''
def collect_traces(binary, processes, results):
	# wait until all processes are done

##	for p in processes:
##		p.join()

	cmdTraces = dict()

##	while not results.empty():
##		result = results.get()

	# collect results and create cmdtraces
	while len(results) != 0:
		result = results.pop()
		print "RESULT: " + str(result)
		inputs = result["inputs"]
		trace = result["trace"]

		# create cfgs
		pinBinary = prepare_pin_binary(binary)
		delimiter = utils.determine_input_bbls(pinBinary)
		os.remove(pinBinary)
		sections = utils.split_trace_by_command(trace, inputs, delimiter)
		if not sections:
			print "split trace by command failed"
			return 1

		# store results in some data structure { "last_cmd" : { "trace": [ perm1, perm2 ] }
		lastCmd = inputs[-1]
		print "LAST_CMD: " + str(lastCmd) + " " + str(inputs)
		try:
			cmdTraces[lastCmd]
		except KeyError:
			cmdTraces[lastCmd] = dict()

					
		trace = '.'.join(s for s in sections[lastCmd])
		perm = '.'.join(i for i in inputs)
		try:
			cmdTraces[lastCmd][trace].append(perm)
		except KeyError:
			cmdTraces[lastCmd] = dict()
			cmdTraces[lastCmd][trace] = [ perm ]

	# identify exit cmds
	exitCmds = check_exit_cmd(cmdTraces.keys(), binary)

	# once done, organize by command and index, and compare
	compare(cmdTraces, exitCmds)
	
'''
	count how many permutations (and which) have the same trace (to distinguish)

'''
def compare(traces, exitCmds):
	# compare
	psm = dict()
	for cmd, value in traces.iteritems():
		if cmd in exitCmds:
			continue
	
		minPermutations = min(map(len, value.values()))
		traceWithMinPerms = filter(lambda i: len(value[i]) == minPermutations, value.keys())
		print traceWithMinPerms
		for t in traceWithMinPerms:
			for exitcmd in exitCmds:
				if exitcmd in t:
					continue
			print "These are different: " + str(value[t])

		
	return 0

	
def check_exit_cmd(cmds, binary):
	exitCmds = []

	for cmd in cmds:
		child = helpers.pexpect_spawn_process(binary)
		rc = helpers.pexpect_send_input_check_exit(child, cmd)
		if rc:
			exitCmds.append(cmd)

	# not all cmds can be exit cmds
	if set(cmds) == set(exitCmds):
		exitCmds = []
	
	print "EXIT CMDS: " + str(exitCmds)
	return exitCmds
