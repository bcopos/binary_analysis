FIND VALID INPUT
=========

These scripts can be used to find valid input for an unknown binary. There are two parts:

* expect script which interacts with the binary
* python script which implements all the logic

The finding of valid input is done by iterating through all the printable characters, one character at a time, for each index of an input string and observing differences in the number of instructions executed between all characters at a given index. A number of instructions executed outside the mode signfies that character may be valid. 
Using an iterative approach, valid input strings can be built.

REQUIREMENTS
------

Although other methods may be used to count instructions, these scripts rely on [perf](https://perf.wiki.kernel.org/index.php/Main_Page).
Please ensure `perf` is installed on the machine where the binary will be run.

WARNING
-----
The expect script is designed to execute binaries remotely (via SSH) on the CGC VM. 
However, it can be simply editted to be used on local binaries.

IMPROVEMENTS
-----

* sample instruction count over time during execution (rather than reporting measurements once at the end for the entire execution)
    * why?
        * if program does random work at beginning (some initialization logic), sampling will help ignore that
        * more efficient (no need to keep restarting binary)
        * can find randomly generated input
    * how?
        * 'I' flag and 'o' flag for output file

ADVANTAGES/USES
-----

* finding input strings for binaries (both good/expect input and bad/unexpected input)
* testing regular expressions used for input validation
* cracking binaries
* determine if hashing algorithm is bad


LIMITATIONS
------

* randomly generated tokens/commands
* hashed tokens/passwords/commands
* input can be anything (no special commands, e.g. an echo server)
 
