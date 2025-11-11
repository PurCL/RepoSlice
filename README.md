# RepoSlice

RepoSlice is an educational framework for implementing LLM-based program slicing. It provides a foundation to learn and implement inter-procedural forward/backward program slicing using LLMs. The framework supports the syntactic analysis support for C/C++ programs (in this project, we only focus on C programs), which further facilitate LLM-driven slicing for a code repository.


## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [What U Need to DO](#what-u-need-to-do)
- [How to Submit](#how-to-submit)
- [How to Grade](#how-to-grade)
- [Contact Us](#contact-us)

## Overview

The key logic should be implemented in the agent `SliceScanAgent` defined in the file `src/agent/slicescan.py`. It performs:

- **Forward Slicing**: Given a seed variable, find all statements that depend on the value of the seed variable.
- **Backward Slicing**: Given a seed variable, find all statements that affect the value of the seed variable.
- **Inter-procedural Analysis**: Trace the dependencies across function calls based on a given call graph

Note that you should collect **both the data dependencies and control dependencies** in the slicing. To support the slicing for a single function, you need to design a prompt and conduct the prompt engineering for the intra-procedural analysis.

## Installation

1. We will grade your submission on `antor.cs.purdue.edu` server. Please make sure your code can run on that server. If you have any issues, please contact TA in advance (See [Contact](#contact-us)). Since it only uses Python and conda, it should be fine to run on your local machine as well.

2. Create and activate a conda environment with Python 3.9.18:

   ```sh
   conda create -n reposlice python=3.9.18
   conda activate reposlice
   ```

3. Install the required dependencies:

   ```sh
   cd RepoSlice
   pip install -r requirements.txt
   ```

4. Ensure you have the Tree-sitter library and language bindings installed:

   ```sh
   cd lib
   python build.py
   ```

   You might encounter the following error during tree-sitter installation:

   ```
   HEAD is now at 12fe553 fix: correct parsing of map types in function parameters
   /Users/XXXX/Downloads/RepoSlice/lib/vendor/tree-sitter-cpp/src/scanner.c:126:5: error: call to undeclared function 'static_assert'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
      static_assert(MAX_DELIMITER_LENGTH * sizeof(wchar_t) < TREE_SITTER_SERIALIZATION_BUFFER_SIZE,
      ^
   1 error generated.
   ```

   **Solution**: Open the file `lib/vendor/tree-sitter-cpp/src/scanner.c` and comment the `static_assert` statement in the following function:
   
   ```c
   unsigned tree_sitter_cpp_external_scanner_serialize(void *payload, char *buffer) {
      // static_assert(MAX_DELIMITER_LENGTH * sizeof(wchar_t) < TREE_SITTER_SERIALIZATION_BUFFER_SIZE,
      //              "Serialized delimiter is too long!");

      Scanner *scanner = (Scanner *)payload;
      size_t size = scanner->delimiter_length * sizeof(wchar_t);
      memcpy(buffer, scanner->delimiter, size);
      return (unsigned)size;
   }
   ```

   Then you can execute `cd lib && python build.py` again for installation.


5. Configure the OpenAI API key:

   ```sh
   export OPENAI_API_KEY=xxxxxx  # add key in `~/.bashrc` or `~/.zshrc`
   source ~/.bashrc  # or source ~/.zshrc
   echo $OPENAI_API_KEY   # should print your key
   ```


## Quick Start

1. We prepare three example projects in `benchmark/Cpp/slice/` for you to have a quick start:

   - Simple Calculator (`simple_calculator/`)
      - **Purpose**: Basic arithmetic operations
      - **Files**: `main.c`
      - **Features**: Multiple code paths, single function

   - Arithmetic Chain (`arithmetic_chain/`)
      - **Purpose**: Sequential arithmetic operations across call levels  
      - **Files**: `main.c`, `level1.c`, `level2.c`, `level3.c`, `operations.h`
      - **Features**: 3-level call depth, complex control flow

   - Data Processing (`data_processing/`)
      - **Purpose**: Data validation and processing pipeline
      - **Files**: `main.c`, `analyzer.c`, `validator.c`, `utilities.c`, `processor.h`
      - **Features**: Conditional branches, loops, performance tracking

   Each example project is designed with:
   - **Complex Control Flow**: Multiple execution paths and conditions
   - **Independent Operations**: Code that doesn't affect main computation
   - **No Pointers**: Uses only basic data types for simplicity
   - **Maximum Call Depth**: 3 levels (main → level1 → level2 → level3)
   - **No Recursions**: No recursive functions in the projects

   When we judge the implementation, we will choose several other projects as slicing subjects, which have the similar complexities as the example projects. Notably, there would be no pointers and recursions in those projects.


2. Test the framework with the provided example projects:

   ```sh
   cd src
   
   # Run a single slice analysis
   ./run_reposlice.sh ../benchmark/Cpp/slice/slice_request_backward_01.json
   
   # Run all slice analyses
   ./run_reposlice_all.sh
   ```

3. After analysis, results will be available in:
   - **Log files**: `log/SliceScanAgent/`
   - **Result files**: `result/SliceScanAgent/`

## What U Need to DO

### Design Your Agent and Prompts

Implement 3 parts:

1. `SliceScanAgent` in `src/agent/slicescan.py`
2. `SliceScanState` in `src/memory/state/slicescan_state.py`.
3. Prompts in `src/prompt/Cpp/slicescan/forward_slicer.json` and `src/prompt/Cpp/slicescan/backward_slicer.json`.

Add your code and overwrite the comments "#TODO ...".
You can define your own classes, functions, and add attributes in existing classes as you need.
Make sure that your output json contains the following attribute:

```
"relevant_function_names_to_line_numbers": {
        "main": [
            1,
            2,
            11,
            15,
            31,
            50
        ],
        "<other_function_1>": [
            1,
            9,
            10,
            12,
            13,
            15,
            16,
            31
        ],
        "<other_function_2>": [
           ...
        ]
    }
```

Notably, we provide a basic version of `src/prompt/Cpp/slicescan/backward_slicer.json`. You can follow its format to design `src/prompt/Cpp/slicescan/forward_slicer.json`. Also, please feel free to revise and polish `src/prompt/Cpp/slicescan/backward_slicer.json` if you want to get better slicing results.

The slicing results of example projects are shown in `oracle/` directory. You don't need to dump `whitelist_line_numbers` in your json file, as they are only used for grading purpose.

Since LLM queries may incur costs, the lecturer will provide each student a reimbursement budget up to $10 for LLM API usage (See below).

### Prepare Your OpenAI Key

To do the reimbursement after submission, please do the following:

  - Create a new project [here](https://platform.openai.com/settings/organization/projects) in your OpenAI account and use a new API key under this new project for Project 3.
  - Keep track of your API usage costs during development. You can check your usage [here](https://platform.openai.com/settings/organization/usage).
  - After submission, please email TA a screenshot of your total usage cost under this new project and details about of your Zelle account (If you don't use Zelle, please email TA for alternative reimbursement methods). TA will reimburse you up to $10 based on your reported usage. 

## How to Submit

Compress your version of `src/` directory ONLY into a file named `proj3_<FirstName>_<LastName>.tar.gz`, and submit it to Brightspace before **Dec 12 11:59pm EST**. Note that you should not modify other files outside the directory `src`. Particularly, you can not load external models. If you want to use other Python packages, please email to us for the approval.

## How to Grade

1. We first manually check your implementation and examine whether you implements all the TODO annotations by following our instructions. If you rely on the LLMs and introduce other simple designs, such as feeding the whole project to the LLMs in one prompt without implementing a worklist algorithm, you will obtain 0 score for the project.

2. We evaluate your slicing results by comparing them against our ground-truth oracle.

   For each slicing request:

   - We first collect all function slices.

   - Then, we concatenate them into a single list, i.e., a list of (function_name, line_number) pairs.

   - Finally, we compute the F1 score between your result and our oracle (see `oracle` directory).

   - Some non-essential lines (e.g., `whitelist_line_numbers` in oracle json file) will be removed from your results during grading and will not affect your score. Concretely, such code lines include the declarations of functions and variables, big brackets, and space lines.

3. We provide grading script `src/utility/judger.py` for you to understand more details about the evaluation process. You can run it as follows (example for `slice_request_forward_01`):

   ```bash
   cd src && ./run_judger.sh slice_request_forward_01 <path_to_result_json.json>
   ```

4. We will run your code using `gpt-4o-mini` five times. We take the highest F1 score among the five runs as your final result.

5. We have given you 6 public test cases and we will evaluate further on 4 hidden test cases. All of them are within the 3 example projects and 6 example slicing requests with similar complexity.

6. Each test case (6 public + 4 hidden) is worth 10 points, for a total of 100 points. For each case, your score is computed as `min(Your_F1_score × 1.25, 1.0) × 10`.


## Contact Us

We will offer a tutorial on Nov 11 (Tue) and release the tutorial recording, from which you can obtain more details about the structure of `RepoSlice` and guidance on the slicer implementation. The slides of the tutorial are included in the directory `docs`.

If you have any further questions, please feel free to reach out to us:

- Chengpeng Wang: wang6590@purdue.edu
- Shiwei Feng: feng292@purdue.edu