from dataclasses import dataclass
from bitstring import Bits
from .processing_element import ProcessingElement, ProcessingElementConfiguration
from .main_buffer import MainBuffer, MainBufferConfiguration
from .instruction import Instruction, MemoryInstruction, ProcessingElementInstruction


@dataclass
class AcceleratorConfiguration:

    # Top Level Specific Values
    COUNTER_BITWIDTH : int
    PE_COUNT         : int

    # Internal Buffer/PE Configurations
    PE_CONFIG        : ProcessingElementConfiguration
    BUFFER_CONFIG    : MainBufferConfiguration

    # Function to Validate Configuration
    def validate(self) -> None:

        # Ensuring the Width of the Main Buffer Matches the
        # Number of PEs in the Array accounting for Input Width
        if (self.PE_COUNT != (self.BUFFER_CONFIG.MEM0_BITWIDTH/self.PE_CONFIG.INPUT_BITWIDTH)):
            raise ValueError(f"Incorrect number of PEs ({self.PE_COUNT}) with input bitwidth {self.PE_CONFIG.INPUT_BITWIDTH} for memory output bitwidth {self.BUFFER_CONFIG.MEM0_BITWIDTH}.")

        # Ensuring the Width of the Main Buffer Matches the PE input bitwidth
        if (self.PE_CONFIG.INPUT_BITWIDTH != self.BUFFER_CONFIG.MEM1_BITWIDTH):
            raise ValueError(f"Incorrect PE input bitwidth {self.PE_CONFIG.INPUT_BITWIDTH} for memory bitwidth {self.BUFFER_CONFIG.MEM1_BITWIDTH}.")

        # Ensuring the Width of the Main Buffer Matches the PE output bitwidth
        if (self.PE_COUNT != (self.BUFFER_CONFIG.MEM2_BITWIDTH/self.PE_CONFIG.OUTPUT_BITWIDTH)):
            raise ValueError(f"Incorrect number of PEs ({self.PE_COUNT}) with output bitwidth {self.PE_CONFIG.OUTPUT_BITWIDTH} for memory input bitwidth {self.BUFFER_CONFIG.MEM2_BITWIDTH}.")
AccelConfig=AcceleratorConfiguration


class Accelerator:

    def __init__(
        self,
        controller_config : AcceleratorConfiguration,
        default_counter_value = 0
    ):

        # Saving the Configuration and Validating
        self._controller_config = controller_config
        self._controller_config.validate()

        # Creating a Bit-Accurate Representation of the Counter
        self._counter = Bits(uint=default_counter_value, length=self._controller_config.COUNTER_BITWIDTH)

        # Creating an Array of PEs
        self._pe_array = [
            ProcessingElement(self._controller_config.PE_CONFIG) for _ in range(self._controller_config.PE_COUNT)
        ]

        # Creating a Main Buffer
        self._main_buffer = MainBuffer(self._controller_config.BUFFER_CONFIG)

    def set_memory(self, mem0 : list[Bits], mem1 : list[Bits]) -> None:
        self.set_mem0(mem0)
        self.set_mem1(mem1)

    def set_mem0(self, mem : list[Bits]) -> None:
        self._main_buffer.set_mem0_bits(mem)

    def set_mem1(self, mem : list[Bits]) -> None:
        self._main_buffer.set_mem1_bits(mem)

    def get_mem2(self) -> list[Bits]:
        return self._main_buffer.read_mem2_bits()

    def execute_instructions(self, instructions : list[Instruction]):
        for inst in instructions:
            self.execute_instruction(inst)

    def execute_instruction(self, instruction : Instruction):
        # START IMPLEMENTATION
        mem_inst = instruction.get_mem_instruction()
        pe_inst  = instruction.get_pe_instruction()
        count    = instruction.get_count().uint
        mema_inc = instruction.get_mema_inc().uint
        memb_inc = instruction.get_memb_inc().uint
        
        #input
        IN = self._controller_config.PE_CONFIG.INPUT_BITWIDTH
        
        #restoring orginal
        original = mem_inst.get_instruction()
        mema_off = mem_inst.get_mema_offset()
        memb_off = mem_inst.get_memb_offset()
        mema = mema_off.uint
        memb = memb_off.uint
        mema_limit = 2 ** len(mema_off)
        memb_limit = 2 ** len(memb_off)

        for step in range(count + 1):

            # 1. memory instruction
            mem_inst.set_mema_offset(mema)
            mem_inst.set_memb_offset(memb)
            self._main_buffer.execute_instruction(mem_inst)

            # 2. run PE
            mem0_word = self._main_buffer.read_mem0_output()
            mem1_word = self._main_buffer.read_mem1_output()
            total = len(mem0_word)

            for i in range(len(self._pe_array)):
                start = total - (i + 1) * IN
                end   = total - i * IN
                pe = self._pe_array[i]
                pe.input_a(mem1_word)
                pe.input_b(mem0_word[start:end])
                pe.execute_instruction(pe_inst)

            # 3. Collect PE's output register into the MEM2 input port
            
            outputs = []
            num_pes = len(self._pe_array)

            for i in reversed(range(num_pes)): # last PE first, PE 0 last
                pe = self._pe_array[i]
                pe_output = pe.get_output()
                outputs.append(pe_output)

            self._main_buffer.write_mem2_input(Bits().join(outputs))

            # 4. Step the offsets for the next repetition
            mema = (mema + mema_inc) % mema_limit
            memb = (memb + memb_inc) % memb_limit

        mem_inst.set_instruction(original)
        # END IMPLEMENTATION
        return 0
