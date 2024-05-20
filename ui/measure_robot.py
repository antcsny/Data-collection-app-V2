import PySimpleGUI as sg
import numpy as np
import traceback
from threading import Semaphore
from typing import Callable

from ui import CollectionGraphWindow
from kuka import KUKA_DataReader, KUKA_Handler

class Measure_robot (CollectionGraphWindow):
    collecting_data_done = False
    N = 100 # WIP : A definir en fonction de la config
    i = 0
    data = None

    latencies = np.zeros(0)
    reads = np.zeros(0)
    writes = np.zeros(0)

    is_tracing = False
    
    def __init__ (self, handler: KUKA_Handler, cell: int, file_prefix: str, temp_dir: str = ".\\temp"):
        
        super().__init__(cell)

        self.cell = cell
        self.name = f"Robot {cell}"
        self.reader = KUKA_DataReader(handler)
        self.file_prefix = file_prefix
        self.temp_dir = temp_dir
        
    def generate_file_name (self, A_iter, speed, sampling, load):
        self.settings = "[" + (speed if type(speed) != slice else f'{speed.start}%-{speed.stop}') + "%] "
        self.settings += f"[{sampling}ms] " 
        self.settings += f"[class {load}] "
        iter = " ".join(A_iter) 
        self.settings += f"[{iter}] " 

        self.file_name = self.file_prefix + " " + self.settings + "- " + self.name
        return self.file_name
    
    def measure_sequence (self, A_iter, speed, sampling, trace_sampling, load: int = -1, lock: Semaphore = None, done: Callable = None):
        
        self.generate_file_name(A_iter, speed, sampling, load)

        print("Starting data collection for " + self.name + " with settings " + self.settings)
        
        def next (latency: float, queue_read: int, queue_write: int):
            # Changer 500 par la taille finale du buffer
            buffer = queue_write - queue_read if queue_read <= queue_write else 500 - queue_read + queue_write
            self.add(buffer, latency)
            self.latencies = np.append(self.latencies, latency)

        try:
            self.data, self.trace_data = self.reader.acquire(A_iter, speed, sampling, trace_sampling, next, done, load, lock, self.temp_dir)            
            self.collecting_data_done = True
            # print("Moyenne Tps Reponse : ",self.data["Read_time"].mean())
            # print("Moyenne Essais : ",self.data["Read_tries"].mean())
            # print("Moyenne Dupliqués : ",self.data["Duplicates"].mean())

        except Exception as e:
            self.collecting_data_done = True
            traceback.print_exception(e)

        self.export_measures()

    def export_measures (self):
        file_name = self.file_name + ".xlsx"
        trace_file_name = self.file_name + "_TRACE" + ".xlsx"

        if self.data is None:
            print(self.name + " failed to collect data")
            return

        try:
            self.data.to_excel(file_name)
            self.trace_data.to_excel(trace_file_name)
        except Exception as e:
            traceback.print_exception(e)
            print("Lost data from " + self.name)

    def _poll (self):
        event, value = self.read(timeout=10)
        if event == sg.WIN_CLOSED or event == '-colexit-':
            self.close()
            return False
        if self.collecting_data_done :
            self.collecting_data_done = False
            self._status.update("Collection Done !",text_color="#0c2")
        else:
            self.redraw()
        return True
