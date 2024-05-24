# Local Imports
from ui import MainWindow, Measure_robot, Measure_latency
from kuka import KUKA_Handler

# Libs
import traceback
import PySimpleGUI as sg
from threading import Semaphore, Thread
from typing import List, Any
import pandas as pd
import matplotlib.pyplot as plt
import os

class MainProgram (MainWindow):
    """Wrapper for the main program. Classes are more reliable than global variables.
    """    

    ### ---- State variables ---- ###
    dataframe = None
    window_latency = []

    ### ---- Robots ---- ###
    robot_handlers: List[KUKA_Handler] = [ None ] * 3
    robot_windows: List[Measure_robot] = [ ]
    
    ### ---- Sync Mechanism ---- ###
    sync_done = 0
    sync_number = 0
    sync_sem = Semaphore(0)

    ### ---- Methods ---- ###
    def __init__(self):
        super().__init__()

        self.update_disabled_ui()

    def open_cell (self, cell: int):
        """Establishes a connection to a robot

        Args:
            cell (int): The number of the cell (from 1 to 3)
        """        

        handler = KUKA_Handler(f"192.168.1.15{cell}", 7000)

        try:
            ok = handler.KUKA_Open()
            if not ok:
                self.write_event_value(f"-rob_errored:{cell}-", None)
                return
        except Exception as e:
            traceback.print_exception(e)
            sg.popup_ok("\n".join(traceback.format_exception(e)))
            self.write_event_value(f"-rob_errored:{cell}-", None)
            return

        self.robot_handlers[cell - 1] = handler    
        self.write_event_value(f"-rob_connected:{cell}-", None)

    def update_disabled_ui (self):
        """Updates the UI based on the robot connections
        """        

        disabled = True
        for i in range(len(self.robot_handlers)):
            r = self.robot_handlers[i]
            disabled = disabled and (r is None)
            self.robots[i].disabled = (r is None)

        self.collection_settings.disabled = disabled
        self.kukatrace.disabled = disabled
        self.latency.disabled = disabled
        self.gripper.disabled = disabled
        self.data.disabled = disabled
                
        self.collection_settings.update_robot_buttons()

    def done (self):
        """Called when a robot has collected the samples for a run. 
        Unlocks the syncing mechanism if all robots are done
        """        

        self.sync_done += 1

        sync_number = 0
        for w in self.robot_windows:
            sync_number += 1 if w is not None and not w.collecting_data_done else 0

        if self.sync_done == sync_number:
            self.sync_done = 0
            self.sync_sem.release(sync_number)

    def close (self):
        """Closes the main program
        """        
        for r in self.robot_handlers:
            if r is not None:
                r.KUKA_Close()
        plt.close("all")

        super().close()

    def start (self, values: Any):
        """Starts the data collection
        """        

        # Check inputs
        if not self.collection_settings.check_configuration():
            print("Failed to run the collection : invalid configuration")
            return

        # Creating the file names
        file_path = values["-user_path-"] + "/" + values["-dataset_name-"]
        if not os.path.exists(values["-user_path-"]):
            os.mkdir(values["-user_path-"])

        # Creating the windows used to collect data
        self.robot_windows = [ ]
        for i in range(len(self.robot_handlers)):
            r = self.robot_handlers[i]
            if r is not None:
                self.robot_windows.append(Measure_robot(r, i + 1, file_path))

        # Initializing the sync mechanism
        self.sync_number = len(self.robot_windows)
        self.sync_sem = Semaphore(0)
        self.sync_done = 0

        # Getting the configuration
        A_iter = [ values[f'num_of_iter{i}'] for i in range(1,7) ]
        speed = self.collection_settings.speed
        sampling = values["-Sys_sampling-"]
        trace_sampling = values["-Trace_config-"]

        # Running the collection for each robot
        for r in self.robot_windows:
            
            r._poll()    # Forces the window to open

            # Reading and writing the files via another thread not to block the main window
            t = Thread(
                target=r.measure_sequence, 
                args=[ 
                    A_iter, speed, sampling, trace_sampling,    # Collection settings
                    self.get_category(r.cell),                  # Sample class
                    self.sync_sem, lambda: self.done()          # Sync mechanism
                ], 
                daemon=False)
            t.start()

        # Unlock the robots at the same time
        self.sync_sem.release(self.sync_number)

    def measure_latencies (self):
        """Runs a latency measurement for each connected robot
        """        

        try:
            self.window_latency = []
            for i in range(len(self.robot_handlers)):
                r = self.robot_handlers[i]
                if r is not None:
                    w = Measure_latency(f"Latency measurement for Robot {i + 1}")
                    w._poll()
                    self.window_latency.append(w)
                    t = Thread(target=w.measure_latency, args=[r], daemon=False)
                    t.start()

        except Exception as e:
            sg.popup_ok(traceback.format_exception(e))
            traceback.print_exception(e)

    def toggle_robot (self, cell: int):
        """Toggles a robot state

        Args:
            cell (int): From 1 to 3, the number of the cell
        """     

        # The robot is already connected   
        if self.robot_handlers[cell - 1] is not None:
            print(f"Trying to disconnect from robot {cell}")
            self.collection_settings.set_robot_connected(cell - 1, False)
            self.robot_handlers[cell - 1].KUKA_Close()
            self.robot_handlers[cell - 1] = None
            self.update_disabled_ui()
            return

        # Connecting to the robot
        self.update_disabled_ui()
        print(f"Trying to connect to robot {cell}")
        self.perform_long_operation(lambda: self.open_cell(cell), "-connect-call-end-")

    def gripper_open (self):
        """Tries to open the gripper of the selected robot
        """        

        if self.robot_handlers[self.gripper._robot_choice - 1] is not None:
            self.robot_handlers[self.gripper._robot_choice - 1].KUKA_WriteVar('PyOPEN_GRIPPER', True)
            self.gripper._btn_open.update(disabled=True)
            self.gripper._btn_close.update(disabled=False)

    def gripper_close (self):
        """Tries to close the gripper of the selected robot
        """        
        if self.robot_handlers[self.gripper._robot_choice - 1] is not None:
            self.robot_handlers[self.gripper._robot_choice - 1].KUKA_WriteVar('PyCLOSE_GRIPPER', True)
            self.gripper._btn_open.update(disabled=False)
            self.gripper._btn_close.update(disabled=True)

    def open_xlsx (self, path: str):
        """Tries to load a .xslx file collected from the system variables

        Args:
            path (str): The path to the file to open
        """        
        try:
            self.dataframe = pd.read_excel(path)
            self.data.update_layout_on_columns(self, self.dataframe.columns)
            self.dataframe['Sample_time_s'] = self.dataframe['Sample']/1000 if 'TRACE' in path else self.dataframe['Sample_time']/1000
            sg.popup("Done")
            self.data.enable_plot_buttons(True)
        except Exception as e:
            sg.popup(e)
            self.data.enable_plot_buttons(False)

    def trace_selected_variables (self):
        plt.close('all')
        a = self.data.get_selected_axis()
        if (len(a)==0):
            sg.PopupOK("Select at least one axis to plot")
            return
        for i, var in enumerate(self.data._var_totrace):
            if(self.data._do_trace_var[i]):
                self.dataframe.plot(x="Sample_time_s",y=[f"{var}_A{i}" for i in a], grid=True),plt.ylabel(f"Motor {var}")
                plt.tight_layout()
            plt.pause(0.1) # Alternative to plt.show() that is not blocking

    def trace_sampling (self):
        self.dataframe.plot(x="Sample_time_s",y=["Queue_Read", "Queue_Write"], grid=True),plt.ylabel("Samples")
        plt.xlabel("Collection execution time (s)")
        plt.twinx(), plt.plot(self.dataframe["Sample_time_s"],self.dataframe['Read_time'], alpha=0.05), plt.ylabel("Request time of the sample (ms)")
        plt.title("Samples in the buffer and red by Python")
        plt.text(10,10,f"Mean ample time : {self.dataframe['Sample_time'].diff().mean()}")
        plt.show()

    def trace_latencies (self):
        self.dataframe.hist(column='Read_time', grid=True, bins=30)
        plt.title("Distribution of the collection time of a sample")
        plt.xlabel(f"Request time (ms) : mean = {self.dataframe['Read_time'].mean().__round__(2)}"),plt.ylabel("Number of samples")
        plt.show()

    def run (self):
        """Runs the main program
        """        

        while True:

            event, values = self.read(timeout=10)

            ## ---- Core Events ---- ##

            if event in (sg.WINDOW_CLOSE_ATTEMPTED_EVENT, sg.WIN_CLOSED, 'Exit'):
                self.close()
                break

            if event == '-equal_iter-':
                for i in range(1, 7):
                    self[f'num_of_iter{i}'].update(value=values['num_of_iter1'])

            if event == '-BTN_start-':
                self.start(values)

            if event == "-dataset_auto-name-":
                self.collection_settings._input_dataset_name.update(value=self.collection_settings.now())

            if event == '-BTN_latency-':
                self.measure_latencies()

            if event == '-doconst_speed-':
                self.collection_settings.update_speed_entry()

            if '-varplot_cbx' in event:
                self.data.update_do()

            ## ---- Robot selector Events ---- ##
            if "rob_select" in event:
                cell = int(event.split(':')[1][:-1])
                self.toggle_robot(cell)
                
            if "rob_connected" in event:
                cell = int(event.split(':')[1][:-1])
                self.collection_settings.set_robot_connected(cell - 1, True)
                self.update_disabled_ui()

            if "rob_errored" in event:
                cell = int(event.split(':')[1][:-1])
                self.collection_settings.set_robot_connected(cell - 1, False, True)
                self.update_disabled_ui()

            ## ---- Gripper Events ---- ##
            if event == '-BTN_open_gripper-':
                self.gripper_open()

            if event == '-BTN_close_gripper-':
                self.gripper_close()

            ## ---- Trace Events ---- ##
            if 'path' in event:
                self[event].Widget.xview_moveto(1)

            if '-open_data' in event :
                nb = int(event.removeprefix("-open_data").removesuffix("-")) # get the identifier of the clicked button
                self.open_xlsx(values[f'-path_data{nb}-'])
                
            if event == '-trace_selvar-':
                self.trace_selected_variables()
            
            if event == '-trace_sample-':
                self.trace_sampling()
                
            if event == '-trace_latency-':
                self.trace_latencies()

            ## ---- Other windows updates ---- ## 

            for i in range(len(self.window_latency)):
                w = self.window_latency[i]
                if w is not None:
                    if w._poll() is False:
                        self.window_latency[i] = None 

            for i in range(len(self.robot_windows)):
                win = self.robot_windows[i]
                
                # Window closed
                if win is None:
                    continue

                # Window closed
                if not win._poll():
                    # Récupérer les données
                    
                    self.robot_windows[i] = None    
                    continue

if __name__ == "__main__":
    main = MainProgram()
    main.run()
    main.close()