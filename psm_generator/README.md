Protocol State Machine Generation
=========

This module attempts to determine the correct (or expected) order of the discovered input strings. 

The process is as follows:

1. for the discovered input strings, compute all permutations of length 2...n (where n = # of strings)
2. for a given permutation, first find arguments for the strings of the permutation
	- this maintains the order of inputs such that if the permutation is "a,b,c", it tries to find arguments for "a", then tries to find arguments for "b" with "a" as its initial command, and so on. Why? In case a previous command affects the argument of the current command.
3. Once arguments are found for all strings, feed the input to an instrument program
	- program is instrumented with a PIN tool which creates a transcript of the basic blocks executed as the program is fed input
4. Split the transcript into parts, each part associated with an input string of the permutation
	- the delimiter used for splitting is obtained by running the instrument program without feeding any input, and taking the last few lines of the transcript. Those lines should represent basic blocks executed by the program before obtaining user input and can be used for delimiters. This is not perfect and could be improved on
5. Given an input string (i.e. "a") take all transcripts where the input string is in the same index of the permutation (e.g. transcripts for "a,b,c" and "a,b,d" are good but "a,b,c" and "b,a,c" are not because "a" is not at the same index). For those transcripts, take all parts pertaining to the given input string. Compare those transcript sections amongst each other and find which differs. 
	- this part is based on the assumption that there are more incorrect permutations of the input strings than correct permutations. This is not perfect nor always true and can definitely be improved on 

CFG data structure
---------------

cfgs = 
{
	cmd: {
		inputs: cfg
	}
}


Splitting Trace files
------------

Trace file usually has the format:

delimiter
trace for cmd 1
delimiter
trace for cmd 2
...

where the delimiter is the set of instructions which represent the reading stdin routine

However, if we attach pin after the binary has been started, the trace will look like:

trace for cmd 1
delimiter
trace for cmd 2

Note, there is no delimiter at the top of the trace since that occurs before pin is attached (just because of the order and timing)

Notes
------

- To run the PIN tool, you may need to first run `echo 0 > /proc/sys/kernel/yama/ptrace_scope` as root
- In order for the PIN tool to work on CGC binaries, they must be convereted to ELF format (cgc2elf utility)
- `cgc.py` is not currently used for anything 

Proposed Improvements
-----

- parallelize tasks
	- there is already some code in place for this but it hasn't been tested, may not even be finished
- better method for determining delimiter to split traces
- better method for identifying "exit"-like commands
- better method for determine valid input strings permutation
