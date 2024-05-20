from .handler import KUKA_Handler
from typing import Any

class KUKA_Array:
    """ Wrapper to manipulate KRL Arrays from Python """

    def __init__(self, name: str, handler: KUKA_Handler, len: int, type = int, default = 0):
        """Wrapper to manipulate KRL Arrays from Python

        Args:
            name (str): The name of the array
            handler (KUKA_Handler): The handler for the connection to the C3 Bridge
            len (int): The length of the array
            type (_type_, optional): The type of variable used int the array. Defaults to int.
            default (int, optional): The default variable if the index does not exist. Defaults to 0.
        """        

        self.type = type
        
        self.len = len
        self.default = default
        self.handler = handler
        self.name = name

    def __read_index (self, index: int):
        """Attempts to read the value at the specified index 

        Args:
            index (int): The index to read

        Returns:
            The read value or self.default
        """            

        v = self.handler.KUKA_ReadVar(f"{self.name}[{index}]")
        if v == b'' or v is None:
            return self.default
        return self.type(v)

    def __getitem__(self, name: int | slice) -> Any:
        """Attempts to read the value(s) at the specified index(es)

        Args:
            index (int): The index(es) to read

        Returns:
            The read value(s) or self.default
        """ 

        if type(name) == slice:
            start = name.start if name.start is not None else 1
            end = name.stop if name.stop is not None else self.len
            step = name.step if name.step is not None else 1

            return [ self.__read_index(i) for i in range(start, end, step) ]
        else:    
            return self.__read_index(name)
    
    def __setitem__ (self, name: int | slice, value):
        """Attempts to write the value(s) at the specified index(es)

        Args:
            index (int): The index(es) to write to
            value: The value to write
        """ 

        if type(name) == slice:
            start = name.start if name.start is not None else 1
            end = name.stop if name.stop is not None else self.len
            step = name.step if name.step is not None else 1

            for i in range(start, end, step):
                self.handler.KUKA_WriteVar(f"{self.name}[{i}]", value)
        else:    
            self.handler.KUKA_WriteVar(f"{self.name}[{name}]", value)
