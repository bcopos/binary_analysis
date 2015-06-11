/*
Copyright (c) 2002-2014 Intel Corporation. All rights reserved.
 
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.  Redistributions
in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.  Neither the name of
the Intel Corporation nor the names of its contributors may be used to
endorse or promote products derived from this software without
specific prior written permission.
 
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE INTEL OR
ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
END_LEGAL */


/*
 *  This file contains an ISA-portable PIN tool for tracing memory accesses.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <map>
#include <sstream>

#include "pin.H"
#include "bloom_filter.hpp"


FILE * trace;
FILE * rw_f;

KNOB<string> KnobStartAddress(KNOB_MODE_WRITEONCE, "pintool", "b", "", "specify starting address of address range");
KNOB<string> KnobSize(KNOB_MODE_WRITEONCE, "pintool", "s", "", "specify ending address of address range");

const static char * begin;
const static char * end;

std::map<string, bool> reads;
std::map<string, bool> writes;
std::map<string, bool> rw;


// Checks if memory address is within range
bool CheckAddressWithinRange(VOID * addr)
{
//    fprintf(rw_f,"%p : %p\n", (void *)strtol(start, NULL, 0), (void *)strtol(end, NULL, 0));
    if ( (void *)addr >= (void *) begin && (void *)addr <= (void *) end ) {
        return true;
    }
    return false;
}

// checks if memory address has been accessed for a read op
//bool CheckRead(VOID * addr) {
bool CheckRead(string addr) {
    return ( reads.find(addr) != reads.end() );
}

// checks if memory address has been accessed for a write op
//bool CheckWrite(VOID * addr) {
bool CheckWrite(string addr) {
    return ( writes.find(addr) != writes.end() );
}

bool CheckRW(string addr) {
    return ( rw.find(addr) != rw.end() );
}

// Print a memory read record
VOID RecordMemRead(VOID * ip, uint32_t size, VOID * addr)
{
    if ( CheckAddressWithinRange(addr) ) {
        stringstream strm;
        strm << addr;
        string addr_str = strm.str();

		if ( ! CheckRead(addr_str) ) {
            reads[addr_str] = true;
        }

		// check if address has been written to (if it has both R&W)
        if ( CheckWrite(addr_str) && ! CheckRW(addr_str) ) {
            rw[addr_str] = true;
            fprintf(rw_f, "%s : %d bytes\n", addr_str.c_str(), size);
        }
        fprintf(trace,"%p: R<%d> %p\n", ip, size, addr);
    }
}

// Print a memory write record
VOID RecordMemWrite(VOID * ip, uint32_t size, VOID * addr)
{
    if ( CheckAddressWithinRange(addr) ) {
        stringstream strm;
        strm << addr;
        string addr_str = strm.str();

        if ( ! CheckWrite(addr_str) ) { 
            writes[addr_str] = true;
        }

		// check if address has been read from (if it has both R&W)
        if ( CheckRead(addr_str) && ! CheckRW(addr_str) ) {
            rw[addr_str] = true;
            fprintf(rw_f, "%s : %d bytes\n", addr_str.c_str(), size);
        }
        fprintf(trace,"%p: W<%d> %p\n", ip, size, addr);
    }
}

// Is called for every instruction and instruments reads and writes
VOID Instruction(INS ins, VOID *v)
{
    // Instruments memory accesses using a predicated call, i.e.
    // the instrumentation is called iff the instruction will actually be executed.
    //
    // On the IA-32 and Intel(R) 64 architectures conditional moves and REP 
    // prefixed instructions appear as predicated instructions in Pin.
    UINT32 memOperands = INS_MemoryOperandCount(ins);

    // Iterate over each memory operand of the instruction.
    for (UINT32 memOp = 0; memOp < memOperands; memOp++)
    {

        if (INS_MemoryOperandIsRead(ins, memOp))
        {
            INS_InsertPredicatedCall(
                ins, IPOINT_BEFORE, (AFUNPTR)RecordMemRead,
                IARG_INST_PTR,
                IARG_MEMORYREAD_SIZE,
                IARG_MEMORYOP_EA, memOp,
                IARG_END);
        }
        // Note that in some architectures a single memory operand can be 
        // both read and written (for instance incl (%eax) on IA-32)
        // In that case we instrument it once for read and once for write.

        if (INS_MemoryOperandIsWritten(ins, memOp))
        {
            INS_InsertPredicatedCall(
                ins, IPOINT_BEFORE, (AFUNPTR)RecordMemWrite,
                IARG_INST_PTR,
                IARG_MEMORYWRITE_SIZE,
                IARG_MEMORYOP_EA, memOp,
                IARG_END);
        }

    }
}

VOID Fini(INT32 code, VOID *v)
{
    fprintf(trace, "#eof\n");
    fclose(trace);
    fclose(rw_f);
}

/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */
   
INT32 Usage()
{
    PIN_ERROR( "This Pintool prints a trace of memory addresses\n" 
              + KNOB_BASE::StringKnobSummary() + "\n");
    return -1;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */

int main(int argc, char *argv[])
{
    if (PIN_Init(argc, argv)) return Usage();

    // use 0 as base if it starts with 0x, else 16
    const char * begin_str = KnobStartAddress.Value().c_str();
	begin = (char *) strtol(begin_str, NULL, 0);
    const char * size_str = KnobSize.Value().c_str();

    rw_f = fopen("rw.out", "w");
//    fprintf(rw_f, "begin: %p\n", begin);

	// size_str+2 to skip '0x', this size is needed for bloom filter size
//	int size_int = atoi(size_str+2);
//	fprintf(rw_f, "size_int: %d\n", size_int);
	int size = (int) strtol(size_str, NULL, 0);
//	fprintf(rw_f, "size_hex: %d\n", size);
	end = begin + size;
//	fprintf(rw_f, "end: %p\n", end);

    trace = fopen("pinatrace.out", "w");

    INS_AddInstrumentFunction(Instruction, 0);
    PIN_AddFiniFunction(Fini, 0);

    // Never returns
    PIN_StartProgram();
    
    return 0;
}
