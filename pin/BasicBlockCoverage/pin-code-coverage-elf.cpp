/*
    pin-code-coverage-measure.cpp - Generate a JSON report with the address of
    each BBL executed.
    Copyright (C) 2013 Axel "0vercl0k" Souchet - http://www.twitter.com/0vercl0k

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.         
*/
#include <pin.H>
#include <jansson.h>
#include <map>
#include <string>
#include <iostream>
#include <set>
#include <list>

#include "filter.H"
FILTER_LIB filter;

struct BASIC_BLOCKS_INFO_T {
    ADDRINT addr;
    UINT32 n;
};

//typedef std::map<ADDRINT, UINT32> BASIC_BLOCKS_INFO_T;
typedef std::list<BASIC_BLOCKS_INFO_T> BASIC_BLOCK_LIST;

///Globals
// The number of the total instruction executed by the program
UINT64 instruction_counter = 0;
// The number of threads
UINT64 thread_counter = 0;
// For each bbl executed, we store its address and its number of instruction

BASIC_BLOCK_LIST bblist;


/// Pintool arguments
// You can specify where the output JSON report will be written
KNOB<std::string> KnobOutputPath(
    KNOB_MODE_WRITEONCE,
    "pintool",
    "o",
    ".",
    "Specify where you want to store the results"
);

// You can set a timeout (in cases the application never ends)
KNOB<std::string> KnobTimeoutMs(
    KNOB_MODE_WRITEONCE,
    "pintool",
    "r",
    "infinite",
    "Set a timeout for the instrumentation"
);


/// Instrumentation/Analysis functions
INT32 Usage()
{
    std::cerr << "This pintool reports a trace of the addresses of each basic block executed in order of execution." << std::endl << std::endl;
    std::cerr << std::endl << KNOB_BASE::StringKnobSummary() << std::endl;
    return -1;
}

// Called right before the execution of each basic block with the number of instruction in arg.
VOID PIN_FAST_ANALYSIS_CALL handle_basic_block(UINT32 number_instruction_in_bb, ADDRINT address_bb)
{
    // What's going on under the hood
    // LOG("[ANALYSIS] BBL Address: " + hexstr(address_bb) + "\n");
	BASIC_BLOCKS_INFO_T basic_blocks_info;
    basic_blocks_info.addr = address_bb;
    basic_blocks_info.n = number_instruction_in_bb;
    bblist.push_back(basic_blocks_info); 

    FILE* f = fopen(KnobOutputPath.Value().c_str(), "a");
    fprintf(f, "address %u ins %u\n", address_bb, number_instruction_in_bb);
    fflush(f);
	fclose(f);
}

// We have to instrument traces in order to instrument each BBL, the API doesn't have a BBL_AddInstrumentFunction
VOID trace_instrumentation(TRACE trace, VOID *v)
{
    if (!filter.SelectTrace(trace))
        return;

    for(BBL bbl = TRACE_BblHead(trace); BBL_Valid(bbl); bbl = BBL_Next(bbl))
    {
        // What's going on under the hood
        // LOG("[INSTRU] BBL Address: " + hexstr(BBL_Address(bbl)) + ", " + hexstr(BBL_NumIns(bbl)) + "\n");
        
        // Insert a call to handle_basic_block before every basic block, passing the number of instructions
        BBL_InsertCall(
            bbl,
            IPOINT_ANYWHERE,
            (AFUNPTR)handle_basic_block,
            IARG_FAST_ANALYSIS_CALL, // Use a faster linkage for calls to analysis functions. Add PIN_FAST_ANALYSIS_CALL to the declaration between the return type and the function name. You must also add IARG_FAST_ANALYSIS_CALL to the InsertCall. For example:

            IARG_UINT32,
            BBL_NumIns(bbl),

            IARG_ADDRINT,
            BBL_Address(bbl),

            IARG_END
        );
    }
}


// Called just before the application ends
VOID pin_is_detached(VOID *v)
{
    //save_instrumentation_infos();
    PIN_ExitProcess(0);
}

VOID this_is_the_end(INT32 code, VOID *v)
{
    //save_instrumentation_infos();
	return;
}

VOID sleeping_thread(VOID* v)
{
    if(KnobTimeoutMs.Value() == "infinite")
        return;

    PIN_Sleep(atoi(KnobTimeoutMs.Value().c_str()));
    PIN_Detach();
}

int main(int argc, char *argv[])
{
    // Initialize PIN library. Print help message if -h(elp) is specified
    // in the command line or the command line is invalid 
    if(PIN_Init(argc,argv))
        return Usage();
    
    /// Instrumentations
    // Register function to be called to instrument traces
    TRACE_AddInstrumentFunction(trace_instrumentation, 0);

    filter.Activate();

    // Register function to be called when the application exits
    PIN_AddFiniFunction(this_is_the_end, 0);
    
    // Register function to be called when a module is loaded
    //IMG_AddInstrumentFunction(image_instrumentation, 0);

    /// Other stuffs
    // This routine will be called if the sleeping_thread calls PIN_Detach() (when the time is out)
    PIN_AddDetachFunction(pin_is_detached, 0);

    // Start the program, never returns
    PIN_StartProgram();
    
    return 0;
}
