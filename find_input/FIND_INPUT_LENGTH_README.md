FINDING INPUT SIZE
======

INTRODUCTION
------

These scripts aim at finding the input size of a binary.
The python script `find_input_size.py` contains most of the logic.
The expect script `expect_input` interacts with the binary and sends input.


EXPLANATION
-----

From observations of CGC binary samples, side channels can be used to detect input size.
The number of instructions executed (most of the time) changes when the input size is surpassed.
Therefore, to find input size, we can look for two things:

1. number of instructions executed changes once input size is surpassed
2. the difference in number of instructions executed for string of size S and S+1 changes once input size is surpassed
	* More specifically, adding an additional character to an invalid input will result in X additional instructions being executed. When the input string surpasses the expected input size (S), the difference in the number of instructions between string of  size S and S+1 is different than that between string of size S-1 and size S.

Three of the following things have been observed:

* number of ins. drops -- usually because program exits or segfaults
* number of ins. increases -- function reading from stdin performs extra steps
* number of ins. stays the same -- program exits but input fed to the program will "spill" onto terminal prompt (this is the trickiest but it also rarely happens, only 1 example DARPA CGC KPRCA3)

Beware, sometimes program may exit prematurely (before reaching input size) because of a segfault. 
There's not much we can do here. Nonetheless, we have determined the input size that will trigger a segfault (we're still OK...)

Using these we can form a method for determining input size.
First, check difference in # of inst. executed for small input size (i.e. "aa" and "aaa" and "aaaa").
The third input is just to double check.
Increase input size and see if delta is the same.
If not, decrease in a binary search manner until limit is found.
If not, increase exponentially.	

SPECIAL CASE:

* delta oscilates between two values (CADET, palindrome)
* num of instr. never changes, program exits when input size > SIZE
	
DISCLAIMER: this is written as a proof of concept and some parts are not very pretty...


