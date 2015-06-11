#!/usr/bin/env python

####
##
## Fuzzer script
##
## Parameters:
## - binary (with path)
## - input
## - protected input
## - results dir 
####

import os
import subprocess
import shutil
import errno
import random
import string
import tempfile
import pexpect

from multiprocessing import Event

from ..helpers import helpers

def fuzzer(binary, inString, protectString, numTries, inputFilesDir, outputFilesDir, segfaultFilesDir, logfile):
	# create folder in tmp directory (for input files before copied to 
	# positive/negative input file directories
	tmpInFile = tempfile.NamedTemporaryFile()

	filename = ''.join(random.choice(string.ascii_uppercase) for i in range(20))

	segfault = False
	binaryProcess = helpers.pexpect_spawn_process(binary)
	inFile = inputFilesDir + "/" + filename
	for i in range(0, numTries):
		# fuzzing input string
		randnum =  str(random.randint(1000, 50000))
		zzufCmd = "bash -c \"/usr/bin/zzuf -i -s " + randnum + " -r 0.9 -P \'" + protectString + "\' -R  \'\\x00-\\x20\\x7f-\\xff\\x23\\x5c\' \""
		child = helpers.pexpect_spawn_process(zzufCmd)
		beforeRc, afterRc = helpers.pexpect_send_input(child, inString.strip())
		if beforeRc or afterRc:
			log(logfile,"zzuf died... (last input = " + inString.strip() + ")")
		helpers.pexpect_kill_process(child)
		fuzzedInput = child.read().split()[-1]

		# write fuzzed input to file
		f = open(inFile, "a")
		f.write(str(fuzzedInput) + "\n")
		f.flush()
		f.close()

		# sending fuzzed input to binary
		beforeRc, afterRc = helpers.pexpect_send_input(binaryProcess, fuzzedInput)
		#print str(fuzzedInput) + " " + str(beforeRc) + " " + str(afterRc)
		if afterRc:
			log(logfile,"Fuzzer died... (last input = " + str(fuzzedInput) + ")")
			if afterRc == 11:
				segfault = True	
			break

		if not binaryProcess.isalive():
			break
	helpers.pexpect_kill_process(binaryProcess)
	
	# write output to file
	outputFile = outputFilesDir + "/" + filename
	with open(outputFile, "w") as of:
		of.write(binaryProcess.read())	
	of.close()

	# check for segfaults
	if segfault:
		segfaultFile = segfaultFilesDir + "/" + filename
		shutil.copyfile(outputFile, segfaultFile)
		shutil.move(inFile, segfaultFile + ".input")
		shutil.move(outputFile, segfaultFile + ".output")

	return 0


def log(logfile, msg):
	with open(logfile, "a") as f:
		f.write(msg + "\n")
		f.close()

###
#
# zzuf captures stdin, fuzzes it, sends to program
# However it prints original input to screen
#
# To correct this, we process output file to reflect what the user should see
#
###
def prep_output(inFile, outFile, inputStr):	
	inputs = open(inFile, "r").read().splitlines()
	origOutF = open(outFile, "r")
	procFile = outFile + ".tmp"
	procOutF = open(procFile, "w")
	i=0
	numLinesF=0

	# Replacing (orig) input string with (zzuf) fuzzed string
	#
	# Expect doesn't realize program died, so it keeps sending input as directed
	# which needs to be fixed. If there is no input (from fuzzed input log file)
	# replace inputStr (un-fuzzed input) with empty string
	origOutF = open(outFile, "r")
	lines = origOutF.read().splitlines()
	for line in lines:
		if line != "":
			if i < len(inputs):
				if inputStr in line:
					procLine = line.replace(inputStr, inputs[i])
					procOutF.write(procLine+"\n")
					i += 1
				else:
					procOutF.write(line+"\n")
			else:
				procOutF.write(line+"\n")
	origOutF.close()
	procOutF.close()	
	shutil.move(procFile, outFile)

# if "fault" is found in file, copy file to segfault files directory
def check_segfault(f, segfault_f, log):
	if "fault" in open(f, "r"):
		# trim lines from the end of the file (due to Segfault error printout)
		trim_segfault_outputFile(f)

		try:
			shutil.copyfile(f, segfault_f)
		except IOError:
			log.write("Problem copy output file to segfault")
			return 0
		return 1
	return 0

def trim_segfault_outputFile(f):
	lineCount = 0
	origF = open(f, "r")
	lines = origF.readlines()
	lineCount = len(lines)
	origF.close()

	procF = open(f+".tmp", "w")
	for line in lines[0,lineCount-6]:
		procF.write(line)
	procF.close()

	shutil.move(f+".tmp", f)

