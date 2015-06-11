import tempfile
import subprocess
import cfg
import time
import os
import random

from ..helpers import helpers


PIN_EXEC = "/home/cgc/pin/pin"
PIN_CODE_COVERAGE_TOOL = "/home/cgc/pin/source/tools/BasicBlockCoverage/obj-ia32/pin-code-coverage-cgc.so"
PIN_EXPECT = "/home/cgc/pintools/code_coverage/scripts/cfg/pin.exp"

def determine_input_bbls(binary):
	# determine sequence of bbls representing waiting for new input
	# run instrumented binary, don't input anything, take last 3 lines as the delimiter
	pin_outfile = tempfile.NamedTemporaryFile(delete=False)
	pin_outfile.close()

	pin_name = pin_outfile.name

	cmd = PIN_EXEC + " -t " + PIN_CODE_COVERAGE_TOOL + " -o " + pin_name + " -- " + binary
	child = helpers.pexpect_spawn_process(cmd)

	time.sleep(1)
	pin_outfile = open(pin_name, "r")
	lines = pin_outfile.readlines()
	input_bbls = lines[-3:]

	# cleanup
	rc = helpers.pexpect_kill_process(child)
	os.remove(pin_name)
	
	return input_bbls

'''
	Splits trace file by commands
	Assumes beginning of trace file is missing
	(assumes binary was started first, then attach pin, hence beginning part of trace is missing)
'''
def split_trace_by_command2(trace, cmds, delimiter):
	f = open(trace, 'r')
	index = 0
	section_num = 0
	sections = dict()
	trace_lines = f.readlines()
	while True:
		if section_num == len(cmds) or index == len(trace_lines):
			break

		line = trace_lines[index]
		if line == delimiter[0] and trace_lines[index+1] == delimiter[1] and trace_lines[index+2] == delimiter[2]:
			index += 3
			section_num += 1
			continue


		try:
			sections[cmds[section_num]].append(line.strip())
		except KeyError:
			sections[cmds[section_num]] = [line.strip()]

		index += 1
	f.close()

	for cmd in cmds:
		if cmd not in sections.keys():
			sections[cmd] = ''

	return sections


def split_trace_by_command(trace, cmds, delimiter):
	# split file by delimiter
	f = open(trace, "r")
	start = 0
	section_start = 0
	section_num = 0
	sections = dict()
#	print delimiter
	for line in f.readlines():
		if start and section_start == 0:
			try:
				sections[cmds[section_num]].append(line.strip())
			except IndexError:
				print "not enough cmds, too many trace file parts (maybe delimiter is wrong)"
				print sections
				print line
				f.close()
				return 1
			except KeyError:
				sections[cmds[section_num]] = [line.strip()]

		if line == delimiter[0]:
			section_start += 1
		if line == delimiter[1] and section_start == 1:
			section_start += 1
		if line == delimiter[2] and section_start == 2:
			section_start = 0
			if start == 0:
				start = 1
			else:
				section_num += 1
	f.close()

	for cmd in cmds:
		if cmd not in sections.keys():
			sections[cmd] = ''

	return sections

def test(binary, cmds, queue):
	pin_outfile = tempfile.NamedTemporaryFile(delete=False)
	input_file = tempfile.NamedTemporaryFile(delete=False)

	pin_name = pin_outfile.name
	in_name = input_file.name	

	# write inputs to file first, then pass them to pin_expect
	for i in cmds:
		input_file.write(i.strip() + "\n")
	input_file.close()
	pin_outfile.close()

	cmd = [PIN_EXPECT + " " + PIN_EXEC + " " + PIN_CODE_COVERAGE_TOOL + " " + pin_name + " " + binary + " " + in_name]
	p = subprocess.call(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	if p != 0:
		print "PIN expect failed"
		print inputs
		print cmd
		return 1

	sections = split_trace_by_command(pin_name, cmds, determine_input_bbls(binary))
	if sections == 1:
		print "sections problem"
		return 1	

	result = sections_cfg(sections)
	result['label'] = str(cmds)
	cmds.sort()
	result['cmds'] = ",".join(cmds)
	queue.put(result)
	return 0

def sections_cfg(sections):
	for key,value in sections.iteritems():
		graph = cfg.data_to_graph(value)
		if graph == None:
			sections[key] = ""
		else:
			dfs = graph.print_tree_dfs()
			sections[key] = ",".join(dfs)
#			s = random.randint(0, 99999)
#			f = open(key + "_" + str(s), 'w')
#			for x in dfs:
#				f.write(str(x)+"\n")
#			f.close()
	return sections

#=========================================================================

def pin_and_cfg(binary, inputs, queue):
	
	pin_outfile = tempfile.NamedTemporaryFile(delete=False)
	input_file = tempfile.NamedTemporaryFile(delete=False)

	pin_name = pin_outfile.name
	in_name = input_file.name	

	# write inputs to file first, then pass them to pin_expect
	for i in inputs:
		input_file.write(i.strip() + "\n")
	input_file.close()
	pin_outfile.close()

	cmd = [PIN_EXPECT + " " + PIN_EXEC + " " + PIN_CODE_COVERAGE_TOOL + " " + pin_name + " " + binary + " " + in_name]
	p = subprocess.call(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	if p != 0:
		print "PIN expect failed"
		print inputs
		print cmd
		return 1

	graph_dict = cfg.run(pin_outfile.name, inputs)
	if not graph_dict:
		print "cfg failed"
		return 1

	queue.put(graph_dict)
	return 0


