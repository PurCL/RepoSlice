from pathlib import Path
from typing import List, Set, Optional, Dict
import json
import time

from llmtool.LLM_utils import *
from llmtool.LLM_tool import *
from memory.utils.api import *
from memory.utils.function import *
from memory.utils.value import *
from utility.errors import RATypeError

BASE_PATH = Path(__file__).resolve().parent.parent.parent


class IntraSlicerInput(LLMToolInput):
    """Input class for intra-procedural program slicing.

    Contains the function to be sliced, seed values, and slicing direction.
    """

    def __init__(
        self, function: Function, seed_list: List[Value], is_backward: bool = True
    ) -> None:
        """Initialize intra-slicer input.

        Args:
            function: Function to be sliced
            seed_list: List of seed values for slicing
            is_backward: Whether to perform backward slicing (default: True)
        """
        assert IntraSlicerInput.check_validity_of_seed_list(
            seed_list
        ), "Invalid seed list"

        self.function = function
        self.is_backward = is_backward
        self.seed_list = sorted(
            set(seed_list), key=lambda seed: (seed.index, seed.name)
        )

        self.seed_description = self.seed_list[0].description()
        self.seed_name = self.seed_list[0].name
        self.seed_type = self.seed_list[0].description()
        self.seed_line_number = self.seed_list[0].line_number_in_function

    @staticmethod
    def check_validity_of_seed_list(seed_list: List[Value]) -> bool:
        """Check if seed list is valid.

        A seed list is valid if it matches one of these cases:
        1. All seeds are return values
        2. All seeds have same location and label
        3. List contains exactly one seed

        Args:
            seed_list: List of seed values to validate

        Returns:
            bool: Whether seed list is valid
        """
        # Case 1: All return values
        labels = [seed.label for seed in seed_list]
        is_return = len(set(labels)) == 1 and ValueLabel.RET in labels

        ## Case 2: The same program location with the same label
        is_same_loc_label = len(set(seed_list)) > 1
        for seed1 in seed_list:
            for seed2 in seed_list:
                if (
                    seed1.file_path != seed2.file_path
                    or seed1.line_number_in_file != seed2.line_number_in_file
                    or seed1.label != seed2.label
                ):
                    is_same_loc_label = False

        # Case 3: Single seed
        is_length_one = len(set(seed_list)) == 1

        return is_return or is_same_loc_label or is_length_one

    def __hash__(self) -> int:
        """Generate hash based on seeds, function and direction."""
        return hash((str(self.seed_list), self.function.function_id, self.is_backward))


class IntraSlicerOutput(LLMToolOutput):
    """Output class containing program slice and external values."""

    def __init__(
        self,
        slice: str,
        ext_values: List[Dict],
        function_str: str,
        line_numbers: List[int],
    ) -> None:
        """Initialize intra-slicer output.

        Args:
            slice: Program slice as string
            ext_values: List of external values used in slice
            function_str: Original function code
        """
        self.slice = slice
        self.function_str = function_str
        self.line_numbers = line_numbers
        """
        An external value is in the following form:
        {
            "type": str,
            "callee_name": Optional[str],
            "index": Optional[int],
            "line_number": Optional[int],
            "variable_name": Optional[str]
        }
        Here are several examples:
        {'type': 'Argument', 'callee_name': 'log_message', 'index': 0, 'line_number': 5, 'variable_name': None}
        {'type': 'Return Value', 'callee_name': None, 'index': None, 'line_number': None, 'variable_name': None}
        {'type': 'Parameter', 'callee_name': None, 'index': 0, 'line_number': None, 'variable_name': None}
        {'type': 'Parameter', 'callee_name': None, 'index': 1, 'line_number': None, 'variable_name': None}
        {'type': 'Output Value', 'callee_name': 'goo', 'index': 2, 'line_number': 6, 'variable_name': None}
        """
        self.ext_values = ext_values

    def __str__(self) -> str:
        """Generate string representation of output."""
        output_str = f"Slice: {self.slice}\n"
        output_str += "External Values:\n"
        for ext_value in self.ext_values:
            output_str += f"{str(ext_value)}\n"
        output_str += f"Line numbers in the slice: {self.line_numbers}\n"
        return output_str


class IntraSlicer(LLMTool[IntraSlicerInput, IntraSlicerOutput]):
    """Tool for performing intra-procedural program slicing using LLM."""

    def __init__(
        self,
        model_name: str,
        temperature: float,
        language: str,
        max_query_num: int,
        logger: Logger,
    ) -> None:
        """Initialize the intra-slicer.

        Args:
            model_name: Name of LLM model to use
            temperature: Temperature parameter for LLM sampling
            language: Programming language being analyzed
            max_query_num: Maximum number of LLM queries allowed
            logger: Logger instance for tracking
        """
        super().__init__(model_name, temperature, language, max_query_num, logger)
        self.backward_prompt_file = (
            f"{BASE_PATH}/prompt/{language}/slicescan/backward_slicer.json"
        )
        self.forward_prompt_file = (
            f"{BASE_PATH}/prompt/{language}/slicescan/forward_slicer.json"
        )

    def _get_prompt(self, input: IntraSlicerInput) -> str:
        """Generate prompt for LLM.

        Args:
            input: Input containing the analysis parameters (type-safe) function and slicing parameters

        Returns:
            Generated prompt string

        Raises:
            RATypeError: If input is not IntraSlicerInput
        """
        if not isinstance(input, IntraSlicerInput):
            raise RATypeError(
                f"Input type {type(input)} is not supported. Expected IntraSlicerInput."
            )

        prompt_file = (
            self.forward_prompt_file
            if not input.is_backward
            else self.backward_prompt_file
        )
        with open(prompt_file, "r") as f:
            prompt_template_dict = json.load(f)

        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_rules"])
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_examples"])
        prompt += "\n" + "\n".join(prompt_template_dict["meta_prompts"])

        question = prompt_template_dict["question_template"].replace(
            "<SEED_DESCRIPTION>", f"{input.seed_description}"
        )
        answer_format = "\n".join(prompt_template_dict["answer_format_cot"])

        prompt = prompt.replace("<FUNCTION>", input.function.lined_code)
        prompt = prompt.replace("<QUESTION>", question)
        prompt = prompt.replace("<ANSWER>", answer_format)

        assert "<SEED_NAME>" not in prompt, (
            "Please remove <SEED_NAME> from the prompt template. "
            "It is kept for compatibility but should not be used."
        )
        assert "<SEED_LINE>" not in prompt, (
            "Please remove <SEED_LINE> from the prompt template. "
            "It is kept for compatibility but should not be used."
        )
        assert "<SEED_TYPE>" not in prompt, (
            "Please remove <SEED_TYPE> from the prompt template. "
            "It is kept for compatibility but should not be used."
        )
        return prompt

    def _parse_response(
        self, response: str, input: IntraSlicerInput
    ) -> Optional[IntraSlicerOutput]:
        """Parse LLM response into slice and external values.

        Args:
            response: Raw response from LLM
            input: Original input for context (type-safe)context

        Returns:
            Parsed slice output or None if parsing fails

        Raises:
            RATypeError: If input is not IntraSlicerInput
        """
        print("Response: \n", response, "\n")
        if not isinstance(input, IntraSlicerInput):
            raise RATypeError(
                f"Input type {type(input)} is not supported. Expected IntraSlicerInput."
            )

        slice_pattern = r"Slice:\s*(.*?)\s*External Variables:"
        ext_values_pattern = r"External Variables:\s*((?:-.*(?:\n|$))+)"
        line_numbers_pattern = r"Line numbers in the slice:\s*\[(.*?)\]\s*$"

        var_pattern = (
            r"^\s*-\s*Type:\s*(?P<type>Output Value|Parameter|Argument|Return Value)\."
            r"(?:\s+Callee:\s*(?P<callee_name>[^\s]+)\.)?"
            r"(?:\s+Index:\s*(?P<index>\d+)\.)?"
            r"(?:\s+Name:\s*(?P<variable_name>[^\s]+)\.)?"
            r"(?:\s+Field Name:\s*(?P<field_name>[^\s.]+)\.)?"
            r"(?:\s+Line:\s*(?P<line_number>\d+)\.)?"
            r"\s*$"
        )

        slice_match = re.search(slice_pattern, response, re.DOTALL)
        if slice_match:
            output_slice = slice_match.group(1).strip()
        else:
            return None

        line_numbers_match = re.search(line_numbers_pattern, response, re.DOTALL)
        if line_numbers_match:
            output_line_number_strings = line_numbers_match.group(1).strip()
            output_line_numbers = [
                int(line_number)
                for line_number in output_line_number_strings.split(",")
            ]
        else:
            output_line_numbers = None

        if output_line_numbers is None:
            return None

        output_ext_values = []
        var_match = re.search(ext_values_pattern, response, re.DOTALL)
        if var_match:
            var_lines = var_match.group(1).splitlines()
            for line in var_lines:
                match = re.match(var_pattern, line)
                if not match:
                    continue
                if match["type"] not in [
                    "Return Value",
                    "Parameter",
                    "Argument",
                    "Output Value",
                ]:
                    continue
                if match["type"] == "Parameter" and match["index"] is None:
                    continue
                if match["type"] == "Argument" and (
                    match["callee_name"] is None
                    or match["index"] is None
                    or match["line_number"] is None
                ):
                    continue
                if match["type"] == "Output Value" and (
                    # index is optional for output values. In C/C++/Java, index is always None and the field index in Value is -1 by default.
                    match["callee_name"] is None
                    or match["line_number"] is None
                ):
                    continue

                ext_value = match.groupdict()

                # Parse the index and line number
                for field in ["index", "line_number"]:
                    if ext_value.get(field) is not None:
                        try:
                            ext_value[field] = int(ext_value[field])
                        except ValueError:
                            ext_value[field] = None
                    else:
                        ext_value[field] = None

                if ext_value.get("field_name") is None:
                    ext_value["field_name"] = None

                output_ext_values.append(ext_value)
        output = IntraSlicerOutput(
            output_slice,
            output_ext_values,
            input.function.lined_code,
            output_line_numbers,
        )
        return output
