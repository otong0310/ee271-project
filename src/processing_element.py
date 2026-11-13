from bitstring import Bits
from .instruction import ProcessingElementInstruction, PEI
from dataclasses import dataclass

# helper functions:
def _split(bits, w):
    total = len(bits)
    n = total // w # number of lanes
    lanes = []

    for i in range(n):
        start = total - (i + 1) * w
        end   = total - i * w
        chunk = bits[start:end]
        lanes.append(chunk.int)
    return lanes

def _pack(vals, w):
    pieces = []

    for v in reversed(vals): # last lane first, so lane 0 ends up on the right
        wrapped = v % 2**w                # wrap into 0 .. 2**w - 1 (two's complement)
        piece = Bits(uint=wrapped, length=w)
        pieces.append(piece)
    return Bits().join(pieces)

def _rnd(A, s): # A / 2**s, ties to even
    d = 2**s  # the divisor
    q = A // d # floor division
    r = A - q * d # remainder
    if 2 * r > d or (2 * r == d and q % 2 == 1):
        q += 1
    return q

@dataclass
class ProcessingElementConfiguration:
    INPUT_BITWIDTH        : int
    ACCUMULATION_BITWIDTH : int
    OUTPUT_BITWIDTH       : int

class ProcessingElement:

    def __init__(
        self,
        config : ProcessingElementConfiguration,
        default_value = 0
    ):

        # Saving Inputs
        self._config = config

        # Creating Bitstrings
        self._input_a_value = Bits(int=default_value, length=self._config.INPUT_BITWIDTH)
        self._input_b_value = Bits(int=default_value, length=self._config.INPUT_BITWIDTH)
        self._acc_value     = Bits(int=default_value, length=self._config.ACCUMULATION_BITWIDTH)
        self._output_value  = Bits(int=default_value, length=self._config.OUTPUT_BITWIDTH)

    def input_a(self, value : Bits) -> None:
        self._input_a_value = value

    def input_b(self, value : Bits) -> None:
        self._input_b_value = value

    # Handling Each Instruction
    def execute_instruction(self, instruction : ProcessingElementInstruction) -> None:
        # START IMPLEMENTATION
        # Your Code Here
        if instruction.get_opcode().uint == PEI.RND:
            self._handle_rnd(instruction)
            return None
        op = instruction.get_value().uint
        if op == PEI.MAC: self._handle_mac(instruction)
        elif op == PEI.OUT:  self._handle_out(instruction)
        elif op == PEI.PASS: self._handle_pass(instruction)
        elif op == PEI.CLR:  self._handle_clr(instruction)
        # END IMPLEMENTATION
        return None

    def _handle_mac(self, instruction : ProcessingElementInstruction):
        # START IMPLEMENTATION
        # Your Code Here
        # END IMPLEMENTATION
        IN  = self._config.INPUT_BITWIDTH
        ACC = self._config.ACCUMULATION_BITWIDTH
        w     = instruction.get_mode_bitwidth()
        n     = IN // w
        acc_w = ACC // n

        a_lanes   = _split(self._input_a_value, w) # input lanes
        b_lanes   = _split(self._input_b_value, w)
        acc_lanes = _split(self._acc_value, acc_w) # accumulator lanes

        new_acc_lanes = []
        for i in range(len(acc_lanes)):
            a = a_lanes[i]
            b = b_lanes[i]
            old_acc = acc_lanes[i]

            product = a * b
            new_acc = old_acc + product

            new_acc_lanes.append(new_acc)

        self._acc_value = _pack(new_acc_lanes, acc_w)
        return None

    def _handle_out(self, instruction : ProcessingElementInstruction):
        # Clamp each signed wide lane to its signed output range; preserve accumulation.
        # START IMPLEMENTATION
        # Your Code Here
        IN  = self._config.INPUT_BITWIDTH
        ACC = self._config.ACCUMULATION_BITWIDTH
        w     = instruction.get_mode_bitwidth()
        n     = IN // w
        acc_w = ACC // n
        OUT = self._config.OUTPUT_BITWIDTH
        out_w = OUT // n

        low = -(2**(out_w - 1)) 
        high =   2**(out_w - 1) - 1

        acc_lanes = _split(self._acc_value, acc_w)

        out_lanes = []
        for A in acc_lanes:
            if A < low:
                clamped = low
            elif A > high:
                clamped = high
            else:
                clamped = A
            out_lanes.append(clamped)

        self._output_value = _pack(out_lanes, out_w)
        
        # END IMPLEMENTATION
        return None

    def _handle_pass(self, instruction : ProcessingElementInstruction):
        # START IMPLEMENTATION
        # Your Code Here
        IN  = self._config.INPUT_BITWIDTH
        ACC = self._config.ACCUMULATION_BITWIDTH
        w     = instruction.get_mode_bitwidth()
        n     = IN // w
        acc_w = ACC // n
        
        self._acc_value = _pack(_split(self._input_a_value, w), acc_w)
        # END IMPLEMENTATION
        return None

    def _handle_clr(self, instruction : ProcessingElementInstruction):
        # START IMPLEMENTATION
        # Your Code Here
        self._acc_value    = Bits(int=0, length=self._config.ACCUMULATION_BITWIDTH)
        self._output_value = Bits(int=0, length=self._config.OUTPUT_BITWIDTH)
        # END IMPLEMENTATION
        return None

    def _handle_rnd(self, instruction : ProcessingElementInstruction):
        # Divide signed wide lanes by 2**unsigned(value), nearest with ties to even; preserve output.
        # START IMPLEMENTATION
        # Your Code Here
        IN  = self._config.INPUT_BITWIDTH
        ACC = self._config.ACCUMULATION_BITWIDTH
        w     = instruction.get_mode_bitwidth()
        n     = IN // w
        acc_w = ACC // n

        s = instruction.get_value().uint

        acc_lanes = _split(self._acc_value, acc_w)
        new_acc_lanes = []
        for A in acc_lanes:
            rounded = _rnd(A, s) # A / 2**s, nearest, ties to even
            new_acc_lanes.append(rounded)

        self._acc_value = _pack(new_acc_lanes, acc_w)

        # END IMPLEMENTATION
        return None

    def get_output(self) -> Bits:
        return self._output_value

    def get_accumulation(self) -> Bits:
        return self._acc_value
