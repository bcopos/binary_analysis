Determining State and State Changes
=======================

** PIN tool is under the pin directory **

State:
- represented as variables (saved to memory) whose value may change throughout a program's execution
- what changes during program execution?
- measured when program is sitting in IO (waiting for user input)
	- Intel PIN tool writes to file as the memory operations happen


EXPECTED BEHAVIOR:
- program writes state variable (local or global) to memory
- program reads state
or vice versa

CHALLENGES:
---------
- filter important memory operations
	- state is preserved in global variables
		- True or False?
		- if True, can we get which addresses pertain to the DATA section
			- probably yes (objdump -h)
	- local temporary variables
		- stack addresses
		- are these really global variables?!
		- Yay or Nay?
		- in what cases are these important/interesting?
			- input determines number of loop iterations
			- authentication (sometimes)
			
- size/type of variable
	- differentiate between int, string, char, float, etc
	- can we observe program's behavior and determine how many it bytes from a given memory address?



OBSERVATIONS:
---------

Writes:
- what the program writes to memory
	- input, temporary varaibles needed for computation

Reads:
- after program enters input, needed for input verification

Example LUNGE 1:
- 35036 r and w (with one input)
- 1293 r and w with program initialization ignored (only RW starting from first input)
- 150 memory addresses both read from and written

Example KPRCA 1:
- user sends "HELLO", program generates and saves passcode, sends "OK [passcode]", user sends input, program verifies input against passcode


V 1.0
--------

Focus only on global/static variables

1) using GDB or objdump, get address range of .data and .bss sections
2) during runtime, monitor addresses accessed and filter address by range
3) from filtered addresses, extract both read from and written to (Intel PIN tool)
	- these _should_ represent state variables and state changes
4) infer type of variable at such memory addresses


TODO:
- compare addresses (to make sure address is within correct range)
	- SOLVED: convert string (address range read in as argument) to void * using strtol(var, NULL, 0)
- modify PIN to also filter addresses
	- obtain/pass range to the PIN tool
		- SOLVED: using KNOB (check inscount0 as an example)
	- ignore memory operations during initialization
		- SOLVED:
			- yes, we get all state variables (because of initialization)
			- no, we only get state variables used to that point of execution
	- extract memory operations both written to and read from
		1) hash map
			- high memory usage?
			- slow?
		2) bloom filters (like 1, but using bloom filters as opposed to hash maps)
- how do we infer type of variable at a given memory address?
	- size of r/w operations via IARG_MEMORYREAD_SIZE
		- not the size of the variable

PIN TOOL
-------

pin -t pinatrace.so -- /path/to/binary

run this where pinatrace.so is located (https://software.intel.com/sites/landingpage/pintool/docs/49306/Pin/html/index.html#EXAMPLES)


Output:
1st column - IP
2nd column - R/W
3rd column - memory address

LINKS:
-----
https://software.intel.com/sites/landingpage/pintool/docs/49306/Pin/html/group__INST__ARGS.html


