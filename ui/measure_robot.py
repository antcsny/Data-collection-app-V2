import PySimpleGUI as sg
import numpy as np
import traceback
from threading import Semaphore
from typing import Callable

from ui import CollectionGraphWindow
from kuka import KUKA_DataReader, KUKA_Handler

class Measure_robot (CollectionGraphWindow):
    """Measurement window for a robot
    """    

    # Flag used to close the window when done
    collecting_data_done = False
    storing_data_done = False

    # Collected data
    data = None
    dosysvar = False
    dotrace = False

    # Latency data [Not used]
    latencies = np.zeros(0)

    def __init__ (self, handler: KUKA_Handler, cell: int, dosysvar: bool, dotrace: bool, file_prefix: str, temp_dir: str = ".\\temp"):
        """Creates a new measurement window, showing the user the progression of the collection
        If system variables collection is enabled in the measurement config, it will plot the number of buffered data and network latency
        If not, it will be a simple window, updating when robot movement is done and when the data file is saved

        Args:
            handler (KUKA_Handler): The Kuka Handler
            cell (int): The number of the cell (from 1 to 3)
            dosysvar / dotrace (bool) : True if the system variable / kuka trace collection method is enabled
            file_prefix (str): The prefix for the output file name     
            temp_dir (str, optional): The temporary working dir for the Kuka Trace parsing. Defaults to ".\temp".
        """        
        
        super().__init__(cell, dosysvar)
        self._dosysvar = dosysvar
        self._dotrace = dotrace

        self.cell = cell
        self.name = f"Robot {cell}"
        self.reader = KUKA_DataReader(handler, dosysvar, dotrace)
        self.file_prefix = file_prefix
        self.temp_dir = temp_dir
        
    def generate_file_name (self, A_iter, speed, sampling, load):
        """Creates a suffix for the output file name containing the acquisition
        parameters

        Args:
            A_iter (List[int]): Number of per-axis iterations
            speed (str|int|slice): The speed (range) of the acquisition
            sampling (int|str): The sampling rate of the system variables
            load (int): The class of the acquisition

        Returns:
            str: The standardized suffix
        """        

        self.settings = "[" + (speed if type(speed) != slice else f'{speed.start}%-{speed.stop}') + "%] "
        self.settings += f"[{sampling}ms] " 
        self.settings += f"[class {load}] "
        iter = " ".join(A_iter) 
        self.settings += f"[{iter}] " 

        self.file_name = self.file_prefix + " " + self.settings + "- " + self.name
        return self.file_name
    
    def measure_sequence (self, A_iter, speed, sampling, trace_sampling, load: int = 0, lock: Semaphore = None, done: Callable = None):
        """Runs the acquisition and saves the result in .xlsx files

        Args:
            A_iter (List[int]): The number of iteration for each axis
            speed (str|int|slice): The speed (range) of the acquisition
            sampling (str|int): The sampling rate of the system variables
            trace_sampling (str): The name of the configuration for KUKA Trace
            load (int, optional): The class of the acquisition. Defaults to 0.
            lock (Semaphore, optional): The semaphore used to sync multiple robots. Defaults to None.
            done (Callable, optional): The function used to declare the end of a run. Defaults to None.
        """        
        
        self.generate_file_name(A_iter, speed, sampling, load)

        print("Starting data collection for " + self.name + " with settings " + self.settings)
        
        def next (latency: float, queue_read: int, queue_write: int):
            # Changer 500 par la taille finale du buffer
            buffer = queue_write - queue_read if queue_read <= queue_write else 500 - queue_read + queue_write
            self.add(buffer, latency)
            self.latencies = np.append(self.latencies, latency)

        try:   
            # launch data collection with configuration
            self.data, self.trace_data = self.reader.acquire(A_iter, speed, sampling, trace_sampling, next, done, load, lock, self.temp_dir)            
            self.collecting_data_done = True

        except Exception as e:
            self.collecting_data_done = True
            traceback.print_exception(e)

        # save data in xlsx file
        self.export_measures()

    def export_measures (self):
        """Exports the internally-stored DataFrames to .xlsx files
        """        

        file_name = self.file_name + ".xlsx"
        trace_file_name = self.file_name + "_TRACE" + ".xlsx"
        
        try:
            if self._dosysvar and self.data is not None:
                self.data.to_excel(file_name)
                print("Successfully stored system variables from " + self.name)
            if self._dotrace and self.trace_data is not None:
                self.trace_data.to_excel(trace_file_name)
                print("Successfully stored kuka traces from " + self.name)
            if (self._dosysvar and self.data is None) or (self._dotrace and self.trace_data is None):
                print(self.name + " failed to collect data")
            self.storing_data_done = True
        except Exception as e:
            traceback.print_exception(e)
            print("Lost data from " + self.name)

    def _poll (self):
        """Updates this window. MUST BE CALLED BY THE MAIN THREAD.

        Returns:
            bool: This window is still opened
        """        

        event, value = self.read(timeout=10)
        
        if event == sg.WIN_CLOSED or event == '-colexit-':
            self.close()
            return False
        
        if self.collecting_data_done :
            self.collecting_data_done = False
            self._status.update("Collection Done",text_color="#00f")
            self._exit.update(disabled=True)
        elif self.storing_data_done :
            self.storing_data_done = False
            self._status.update("Successfully stored data", text_color='#0c2')
            self._exit.update(disabled=False)
        elif self._dosysvar:
            self.redraw()
        if not self._dosysvar:
            self._subtitle.update("Kuka trace started\nRobot running")
        return True
    
