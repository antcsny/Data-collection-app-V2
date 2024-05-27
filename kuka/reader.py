import dateutil.tz
from time import sleep, time
import pandas as pd
from typing import Callable, List, Tuple
from threading import Semaphore
from datetime import datetime

from .handler import KUKA_Handler
from .trace import KUKA_Trace

TZ = dateutil.tz.gettz("Europe/Prague")

def trad_bool(input:bytes):
    out = [0]*len(input)
    for i in range(len(input)):
        if(input[i]==b'TRUE'):
            out[i]=True
        if(input[i]==b'FALSE'):
            out[i]=False
    return out


class KUKA_DataReader:
    """ Used to use the live data collection system """
    
    # Flags used to sync the robot state with the local state
    _read_done = False
    _data_available = False
    _speed = 0

    # The columns order of the read data, used to create the DataFrame
    _columns = [
        "Sample_time",
        "Position_Command_A1", "Position_A1", "Torque_A1", "Current_A1", "Temperature_A1",
        "Position_Command_A2", "Position_A2", "Torque_A2", "Current_A2", "Temperature_A2",
        "Position_Command_A3", "Position_A3", "Torque_A3", "Current_A3", "Temperature_A3",
        "Position_Command_A4", "Position_A4", "Torque_A4", "Current_A4", "Temperature_A4",
        "Position_Command_A5", "Position_A5", "Torque_A5", "Current_A5", "Temperature_A5",
        "Position_Command_A6", "Position_A6", "Torque_A6", "Current_A6", "Temperature_A6",
        "A1", "A2", "A3", "A4", "A5", "A6" ,     
        "Queue_Read", "Queue_Write", "Load", "Faulty", "Speed", "Read_time",
    ]

    # TAB1 Length
    __TAB1_LEN = 36
    
    # TAB1 data indexes 
    __TAB1_SAMPLE = 0
    __TAB1_SAMPLE_READ = 32
    __TAB1_SAMPLE_WRITE = 33
    __TAB1_DATA_START = 1
    __TAB1_DATA_END = 31
    __TAB1_MOTOR = 31
    __TAB1_DATA_AVAILABLE = 34
    __TAB1_DONE = 35

    def __init__(self, handler: KUKA_Handler) -> None:
        """Creates a new Data Reader

        Args:
            handler (KUKA_Handler): The C3 Bridge Connection handler
        """        

        self.handler = handler

        # KUKA TRACE
        self.trace = KUKA_Trace(handler)
        self.trace.Trace_Enable(True)

    def __read (self, name: str, default = None):
        """Tries to read a value from the C3 interface, or returns a default
        value.

        Args:
            name (str): The name of the varaible to read
            default (_type_, optional): The default value to return. Defaults to None.

        Returns:
            The variable read or the default value
        """        

        r = self.handler.KUKA_ReadVar(name)
        if r is None or r == b'':
            return default
        return r
    
    ### This section defines setter/getters to change the variables used by ###
    ### the data collector sub                                              ###

    ## ColRUN
    @property
    def ColRUN (self) -> bool:
        return self.__read("ColRUN", False)
    
    @ColRUN.setter
    def ColRUN (self, value: bool):
        self.handler.KUKA_WriteVar("ColRUN", value)

    ## PyDONE
    @property
    def PyDONE (self) -> bool:
        return self.__read("PyDONE", False)
    
    @PyDONE.setter
    def PyDONE (self, value: bool):
        self.handler.KUKA_WriteVar("PyDONE", value)

    ## __PYTHON_HAS_READ
    @property
    def HAS_READ (self) -> int:
        return self.__read("__PYTHON_HAS_READ", 0)
    
    @HAS_READ.setter
    def HAS_READ (self, value: int):
        self.handler.KUKA_WriteVar("__PYTHON_HAS_READ", value)

    ### ------------------------------------------------------------------- ###

    def __try_get_data (self, name: str) -> bytes:
        """Tries to read a variable via the C3 interface up to 10 times

        Args:
            name (str): The name of the variable to read

        Raises:
            Exception: The read operation failed 10 times in a row

        Returns:
            bytes: The read data
        """        

        tries = 0
        r: bytes = b''
        while (r == b'' or r is None) and tries < 10:
            r = self.handler.KUKA_ReadVar(name)
            tries += 1
        if (r == b'' or r is None):
            raise Exception("Failed to read " + name)
        return r

    def __format_motor_value (self, motor: int):
        """Converts the analog output reading to 7 columns boolean values

        Args:
            motor (int): The analog value

        Returns:
            List[int]: The 7 columns reprensenting the motor states
        """        

        return [ (1 if i == motor else 0) for i in range(1,7) ]

    ## Get data
    def get_data (self) -> Tuple[List[float|int], bool, int]:
        """Collects the latest sample made available by the Data collector sub

        Raises:
            Exception: "Incomplete Tab 1 !": Not all columns have been read

        Returns:
            List[float|int]: The sample
        """        

        r1: bytes = self.__try_get_data("__TAB_1[]")
        raw = r1.split(b" ")[:-1]
        if len(raw) != self.__TAB1_LEN:
            print("Invaild raw data :", raw)
            raise Exception("Incomplete Tab 1 !")
        
        TAB1 = [ float(raw[i]) for i in range(len(raw)) ]           # Bytes to float conversion

        data = [
            TAB1[self.__TAB1_SAMPLE],                               # Sample time
            *TAB1[self.__TAB1_DATA_START:self.__TAB1_DATA_END],     # Per-axis data
            *self.__format_motor_value(TAB1[self.__TAB1_MOTOR]),    # Motor status columns
            TAB1[self.__TAB1_SAMPLE_READ],                          # Queue Read 
            TAB1[self.__TAB1_SAMPLE_WRITE],                         # Queue Write
        ]

        return (
                data, 
                TAB1[self.__TAB1_DATA_AVAILABLE] == 1,              # Data available flag
                TAB1[self.__TAB1_DONE]                        # PyDone status
                )

    ## Reading function for the queue
    def read (self, time_before, load: int = 0) -> Tuple[List[float|int], bool, int]:
        """Reads a sample from the data collection sub

        Args:
            time_before (_type_): The time at which the latest successful read has occured (for latency calculation)
            load (int, optional): The the class of the sample. Defaults to 0.

        Returns:
            Tuple[List[float|int], bool, bool]: The read data, data available flag and PyDone flag
        """        

        data, data_available, done = self.get_data()
        now = time()
        data.append(load)                       # Load label
        data.append(1 if load == 0 else 0)      # Faulty label
        data.append(f'{self._speed}%')          # Speed Label
        data.append((now - time_before) * 1000) # Request Time
        return data, data_available, done
        

    def reset (self):
        """Resets the data collection sub
        """        

        self._read_done = False
        self._data_available = False
        self.handler.KUKA_WriteVar("SAMPLE_NUMBER", 1)
        self.handler.KUKA_WriteVar("SAMPLE_READ", 1)
        self.handler.KUKA_WriteVar("__PyResetTimer", True)
                                       
    def init (self, A_iter: List[str], speed: str, sampling: str):
        """Prepares and starts data collection

        Args:
            A_iter (List[str]): The number of iterations per axis
            speed (str): The speed for this run
            sampling (str): The sampling rate in ms
        """        

        self.rate = int(sampling)/1000
        
        # Writing parameters        
        for i in range(1,7):
            self.handler.KUKA_WriteVar(f'PyITER[{i}]', A_iter[i - 1])

        self.handler.KUKA_WriteVar('PySPEED', speed)
        self._speed = int(speed)
        self.handler.KUKA_WriteVar('ColSAMPLING', sampling)

        # Waiting for Reset
        self.handler.KUKA_WriteVar('ColRESET', True)
        sleep(0.1)
        while not self.handler.KUKA_ReadVar('ColRESET_DONE'):
            sleep(0.2)

        sleep(0.5)
        self.handler.KUKA_WriteVar('PyRUN', True)
        self.handler.KUKA_WriteVar('ColRUN', True)
        sleep(0.1)

    def run (
            self, 
            next: Callable[[float, int, int], None] = None, 
            load: int = -1
        ) -> pd.DataFrame:
        """Runs data collection using system variables

        Args:
            next (Callable[[float, int, int], None], optional): A function used to update the user interface in order to show the current progress. Defaults to None.
            load (int, optional): The class of the sample. Defaults to -1.

        Returns:
            pd.DataFrame: The collected data 
        """               
        
        # Indexes of control data in the raw readings
        __SAMPLE_READ_INDEX = -6
        __SAMPLE_WRITE_INDEX = -5
        __SAMPLE_LATENCY = -1

        # Buffers
        frames = []
        
        # Time data to calculate latency
        now = time()

        # Flag indicating the state of the collection
        self._read_done = False
        trace_stoped = False
        
        while self._read_done != 1 :
            
            # Getting our sample
            data, self._data_available, self._read_done = self.read(now, load)
            
            # Checking if some data is available
            if (self._data_available):
                
                # Getting the last sample number. Defaults to 0 which does not exist in KRL
                before = 0 if len(frames) == 0 else frames[-1][__SAMPLE_READ_INDEX]

                # Getting the current sample number. Starts at 1
                after = data[__SAMPLE_READ_INDEX]

                # Ignore duplicates
                if before == after:
                    sleep(self.rate)
                    continue
                
                # Indicating to the sub that we read the sample
                self.HAS_READ = after
                
                # Resetting the current time to measure the next request delay
                now = time()
                
                # Storing the currently measured data
                frames.append(data)

                # Callback to give a visual feedback on current data collection
                if next is not None:
                    next(data[__SAMPLE_LATENCY], data[__SAMPLE_READ_INDEX], data[__SAMPLE_WRITE_INDEX])
            
                # Sleeping not to slow down KRL
                sleep(self.rate/2)

            else:
                # Sleeping to wait for the next data to be sampled, stop de trace if robot movement done
                if self._read_done == 2 and not(trace_stoped):
                    trace_stoped = True
                    self.trace.Trace_Stop()
                sleep(self.rate/2)
        
        # Creating a data frame
        return pd.DataFrame(frames, columns=self._columns)
    
    def get_trace_data (
            self, 
            speed: int | str, 
            load: int,
            sampling: int,
            dir: str = ".\\temp",
            sampling_offset: int = 0
        ) -> Tuple[pd.DataFrame, int]:
        """Gets the Kuka Trace data

        Args:
            speed (int | str): The speed at which the run was made
            load (int): The class of the sample
            sampling (int): The sampling rate of the Kuka Trace
            dir (str, optional): The folder in which to store the files to process. Defaults to ".\temp".
            sampling_offset (int, optional): The index of the first sample. Defaults to 0.

        Returns:
            Tuple[pd.DataFrame, int]: The collected data and the number of samples
        """        

        data_trace = self.trace.Trace_Download()
        
        dataset_length = len(data_trace['Sample_time'])
        data_trace['Speed'] = [int(speed)] * dataset_length

        if load == 0:
            data_trace['Faulty'] = [0] * dataset_length
        else:
            data_trace['Faulty'] = [1] * dataset_length
        
        data_trace['Load'] = [load] * dataset_length

        return (pd.DataFrame(data_trace), dataset_length)

    def acquire (
            self, 
            A_iter: List[str], 
            speed: str | int | slice, 
            sampling: str, 
            trace_config = "12_ms",
            next: Callable[[float], None] = None, 
            done: Callable = None,
            load: int = -1,
            lock: Semaphore = None,
            temp_dir: str = None
        ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Collects a full dataset using both system variables and Kuka Traces

        Args:
            A_iter (List[str]): The number of iteration per axis
            speed (str | int | slice): The speed (range) at which to run the iterations
            sampling (str): The system variables sampling time
            trace_config (str, optional): The trace configuration file name. Defaults to "12_ms".
            next (Callable[[float], None], optional): A function used to update the user interface in order to show the current progress. Defaults to None.
            done (Callable, optional): A function which is called at the end of a run. Used to sync multiple robots. Defaults to None.
            load (int, optional): The dataset class. Defaults to -1.
            lock (Semaphore, optional): A lock used to sync multiple robots. Defaults to None.
            temp_dir (str, optional): The folder in which to store the files to process. Defaults to None.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: The system variables Dataframe and the Kuka Trace DataFrame
        """        

        # Reset the sub
        self.reset()

        # Using current date as a unique file name for the Kuka Traces
        now = datetime.now(tz=TZ).strftime("%Y-%m-%d_%H-%M-%S")

        # Making sure that Kuka Trace is stopped
        self.trace.Trace_Stop()

        # Getting the Kuka Trace sampling rate from the file name
        trace_sampling = int(trace_config.split("_")[0])

        ## ---- Run for a single speed ---- ##
        if type(speed) == str or type(speed) == int:

            # Sync with other robots
            if lock is not None:
                lock.acquire()
            
            # KUKA Trace
            cell = self.handler.ipAddress.split(".")[3][-1]
            file_name = now + f"[{speed}]_R{cell}"
            self.trace.Trace_Config([ file_name, trace_config , "600" ])
            self.tracing = self.trace.Trace_Start()
            if self.tracing:
                print("Trace start for " + self.handler.ipAddress)
            else:
                print("Could not start trace for " + self.handler.ipAddress)

            # KRL System Variables
            self.init(A_iter, speed, sampling)
            data_vars = self.run(next, load)
            
            # KUKA Trace
            if self.tracing:
                # self.trace.Trace_Stop()
                # sleep(5)
                data_trace, _ = self.get_trace_data(speed, load, trace_sampling, temp_dir)

            # Indicating the end of this run
            if done is not None:
                done()
            
            # Returning the two collected DataFrames
            return data_vars, data_trace
        ## -------------------------------- ##

        ## ---- Run for multiple speeds ---- ##

        start = speed.start if speed.start is not None else 20
        step = speed.step if speed.step is not None else 10
        stop = speed.stop if speed.stop is not None else start
       
        # Buffers 
        dataframes = []
        trace_dataframes = []
        trace_offset = 0

        while start <= stop:

            # Sync with other robots
            if lock is not None:
                lock.acquire()
            
            # Print current speed to the terminal
            print(f"Run with speed {start}")
            
            # KUKA Trace
            cell = self.handler.ipAddress.split(".")[3][-1]
            file_name = now + f"[{start}]_R{cell}"
            self.trace.Trace_Config([file_name, trace_config, "600"])
            self.tracing = self.trace.Trace_Start()
            if self.tracing:
                print("Trace start for " + self.handler.ipAddress)
            else:
                print("Could not start trace for " + self.handler.ipAddress)

            # KRL System Variables
            self.init(A_iter, start, sampling)
            self.LAST_RUN = start == stop
            df = self.run(next, load)  
            
            # KUKA Trace
            if self.tracing:
                self.trace.Trace_Stop()
                sleep(0.1)
                data_trace, size = self.get_trace_data(start, load, trace_sampling, temp_dir, trace_offset)
                
                # Updating the offset
                trace_offset += size

                # Storing the resulting DataFrame in the buffer
                trace_dataframes.append(data_trace)

            # Indicating that this run is done
            if done is not None:
                done()
            
            # Storing the resulting DataFrame in the buffer
            dataframes.append(df)  
            start += step 

        # Merging the results for each speed into one monolithic DataFrame for each method
        return pd.concat(dataframes), pd.concat(trace_dataframes)
    
        ## --------------------------------- ##
