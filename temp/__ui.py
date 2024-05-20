import PySimpleGUI as sg
import numpy as np
import threading as th
from datetime import datetime
from dateutil import tz
from time import time, sleep, time_ns
import os
import pandas as pd
import matplotlib.pyplot as plt
from kuka import KUKA_DataReader, KUKA_Handler
import traceback
from graph_window import CollectionGraphWindow
from threading import Semaphore
from typing import Callable

TZ = tz.gettz("Europe/Prague") 
sg.theme("SystemDefaultForReal")

class UI_Collection_Settings (sg.Frame):
    # Class flags 
    _disabled = False
    _constant_speed = True
    _do_tq = True
    _do_curr = True
    _do_temp = True
    _do_posact = False
    _do_posreal = False
    # Robot staus variables
    _not_connected = "#99c"
    _connected = "#3f3"
    _errored = "#f33"
    _robot_status = [ _not_connected, _not_connected, _not_connected ] 

    def __init__ (self):
        """_summary_ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window for the configuration related elements
        sg elements like checkbox and buttons are stored in the class to be accessed easily
        Return : sg.Frame
        """
        super().__init__("Collection Settings", self.__make_layout())

    def __make_layout (self):

        now = self.now()
        self._input_dataset_name = sg.InputText(now, key='-dataset_name-', size=(30, 1), font=("Consolas", 10))
        
        dir_path = os.path.dirname(os.path.realpath(__file__)) + "/data"
        self._input_working_dir = sg.Input(default_text=dir_path, key='-user_path-', size=(40, 1), font=("Consolas", 10))
        self._input_browse_dir = sg.FolderBrowse(initial_folder=dir_path, key='-browse-')

        self._input_iterations = []
        for i in range(1,7):
            self._input_iterations.append(sg.InputText('1',key=f'num_of_iter{i}',size=(5,1), font=("Consolas", 10)))
        
        self.domeas_tq = sg.Checkbox('$TORQUE_AXIS_ACT', key='-domeas_tq-', size=(25, 1), enable_events=True,  default=True)
        self.domeas_curr = sg.Checkbox('$CURR_ACT', key='-domeas_curr-', size=(25, 1), enable_events=True, default=True)
        self.domeas_tptr = sg.Checkbox('$MOT_TEMP', key='-domeas_tprt-', size=(25, 1),enable_events=True, default=True)
        self.domeas_posact = sg.Checkbox('$AXIS_ACT', key='-domeas_posact-', size=(25, 1), enable_events=True, default=False)
        self.domeas_posreal = sg.Checkbox('$AXIS_ACT_MEAS', key='-domeas_posreal-', size=(25, 1), enable_events=True, default=False)

   
        self.sample_rate = sg.Combo(['12','24', '36', '48', '60'], default_value='12', key='-Sys_sampling-')

        self.doconst_speed = sg.Checkbox('Constant', key='-doconst_speed-', size=(25, 1),enable_events=True, default=True)
        self._input_min_speed =  sg.InputText('30', key='-rob_speed_min-', size=(3, 1), font=("Consolas", 10))
        self._input_max_speed =  sg.InputText('40', key='-rob_speed_max-', size=(3, 1), font=("Consolas", 10), disabled=True)
        self._input_speed_step = sg.InputText('10', key='-rob_speed_step-', size=(3, 1), font=("Consolas", 10), disabled=True)

        self._robot_selector = [ sg.Button(f"Robot {i}", key=f"-rob_select:{i}-") for i in range(1,4) ]

        self._layout = [
            [ sg.Text("Dataset name :"), self._input_dataset_name, sg.Button("Auto Name", key="-dataset_auto-name-", font=("Consolas", 10)) ],
            [ sg.Text("Working directory :"), self._input_working_dir, self._input_browse_dir ],
            [ sg.Text("Number of iterations from axis A1 to A6 : "), sg.Push(), *self._input_iterations, sg.Button("All = A1",key='-equal_iter-',font=("Consolas", 10)) ],
            [
                [sg.Text('Variables to collect :')],
                [self.domeas_tq, sg.Text('Motor torque of an axis (torque mode)')],
                [self.domeas_curr, sg.Text('Motor current of an axis')],
                [self.domeas_tptr, sg.Text('Motor temperature of an axis (~ precision)')],
                [self.domeas_posact, sg.Text('Axis-specific setpoint position of the robot')],
                [self.domeas_posreal, sg.Text('Axis-specific real position of the robot')]
            ],
            [ sg.Text('Variable sampling rate (ms):'), self.sample_rate],
            [
                sg.Text("Robot speed :"),   self.doconst_speed, sg.Push(),  
                sg.Text("From :"),          self._input_min_speed,
                sg.Text("% To :"),          self._input_max_speed,
                sg.Text("% Step :"),      self._input_speed_step
            ],
            [ sg.Text("Selected robots : "), sg.Push(), *self._robot_selector ]
        ]
        return self._layout
    
    def now (self):
        """_summary_
        Give the formated date time  
        Returns: _type_: str
        """
        return datetime.now(tz=TZ).strftime("[%Y-%m-%d] %Hh%M data")
    
    def update_speed_entry(self):
        """_summary_
        Update the sate (disabled or enabled) of the inputs of robot speed depending on the state of the checkbox "Constant"
        If constant, the Min speed will be considerated in the robot run
        """
        self._constant_speed = bool(self.doconst_speed.get())
        self._input_max_speed.update(disabled=self._constant_speed, text_color="#000")
        self._input_speed_step.update(disabled=self._constant_speed, text_color="#000")

    def update_robot_buttons (self):
        """_summary_:
        updates the color of the button clicked to select a robot depending on the status
        """
        for i in range(len(self._robot_selector)):
            btn = self._robot_selector[i]
            btn.update(button_color=self._robot_status[i])
    
    def set_robot_connected (self, cell: int, connected: bool, errored: bool = False):
        """_summary_
        updates the state of the variable _robot_status, giving the state of the robots
        Args:
            cell (int): nuber of the robot (1,2,3)
            connected (bool): give True to indicate that the connection to the robot is successful
            errored (bool, optional): Defaults to False, give True if the robot connection is errored
        """
        if errored:
            self._robot_status[cell] = self._errored
            return
        self._robot_status[cell] = self._connected if connected else self._not_connected
    
    def update_domeas (self):
        """_summary_
        Update the state of the variables domeas_XXX if a checkbox is clicked
        """
        self._do_tq = bool(self.domeas_tq.get())
        self._do_curr = bool(self.domeas_curr.get())
        self._do_temp = bool(self.domeas_tptr.get())
        self._do_posact = bool(self.domeas_posact.get())
        self._do_posreal = bool(self.domeas_posreal.get())
        
    def check_configuration(self):
        """_summary_
        Configuration check before launching a mesure of the robot variables, insure that all the parameters are correct :
            axis iterations, robot speed
        Returns:
            _type_: configuration correct ? True/False
        """
        config_errors = []
        try:
            for axis in self._input_iterations:
                if not 99 >= int(axis.get()) >= 0:
                    config_errors.append('- Number of axis iteration must be from 0 to 99\n')
                    break
        except ValueError:
            config_errors.append('- Number of axis iteration must be integer value\n')
        try:
            if not 100 >= int(self._input_max_speed.get()) >= 1:
                config_errors.append('- Robot max speed must be from 1 to 100 %\n')
            if not 100 >= int(self._input_min_speed.get()) >= 1:
                config_errors.append('- Robot max speed must be from 1 to 100 %\n')
            if not 100 >= int(self._input_speed_step.get()) >= 1:
                config_errors.append('- Robot step speed must be from 1 to 100 %\n')
        except ValueError:
            config_errors.append('- Robot speed be integer value\n')

        if not bool(config_errors):
            return True
        else:
            sg.popup_ok(''.join(config_errors), title='ERROR', font=16, modal=True)
            return False

    @property # called when : print(disabled)
    def disabled (self):
        return self._disabled
    
    @disabled.setter # called when : disabled = True/False
    def disabled (self, v: bool):
        """_summary_
        Disable all the interactions with widgets of the frame to prevent modifications
        Make it clear to the user that no robot is connected
        Args:
            v (bool): disable the entries of the entire frame ?
        """
        self._disabled = v

        self.domeas_tq.update(disabled=v)
        self.domeas_curr.update(disabled=v)
        self.domeas_tptr.update(disabled=v)
        self.domeas_posact.update(disabled=v)
        self.domeas_posreal.update(disabled=v)
        
        self._input_dataset_name.update(disabled=v, text_color="#000")
        self._input_working_dir.update(disabled=v, text_color="#000")
        self._input_browse_dir.update(disabled=v)
        self._input_min_speed.update(disabled=v, text_color="#000")
        self._input_max_speed.update(disabled=self._constant_speed or v, text_color="#000")
        self._input_speed_step.update(disabled=self._constant_speed or v, text_color="#000")
        self.doconst_speed.update(disabled=v)
        
        self.sample_rate.update(disabled=v)
        
        for s in self._input_iterations:
            if not isinstance(s, sg.Text):
               s.update(disabled=v, text_color="#000")

    @property   ##################################################################################### A completer #######################################################################""
    def speed (self) -> str | slice:
        """Returns the speed configuration. If the speed is marked as constant, 
        it returns a string. If the speed is not constant, it returns a splice
        object which contains the minimum speed, the maximum speed and the step.

        Returns:
            str | slice: The speed configuration
        """        
        if self._constant_speed:
            return self._input_min_speed.get()
        
        min = int(self._input_min_speed.get())
        max = int(self._input_max_speed.get())
        step = int(self._input_speed_step.get())

        return slice(min, max, step)
    
class UI_KUKATrace( sg.Frame):
    _disabled = False

    def __init__ (self):
        """_summary_ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window for the Kuka trace related elements
        sg elements like checkbox and buttons are stored in the class to be accessed easily
        Return : sg.Frame
        """     
        super().__init__(f"KUKA Trace", self.__make_layout(), expand_x=True)

    def __make_layout (self):

        self._sampling_rate = sg.Combo(['12_ms','12_ms_v2','4_ms'], key='-Trace_config-', default_value='12_ms', size=(20, 1))
        self._do_delfile = sg.Checkbox('Delete files from KRC?',key='-delete-',default=True, disabled=True)

        self._layout = [
            [ sg.Text('Trace Sampling rate:'), self._sampling_rate,  self._do_delfile ]
        ]    

        return self._layout

    @property # called when : print(disabled)
    def disabled (self):
        return self._disabled
    
    @disabled.setter  # called when : disabled = True/False
    def disabled (self, v: bool):
        """ Give the disabled state v to the Combo entry for the sampling rate to disable it"""
        self._disabled = v

        self._sampling_rate.update(disabled=v)
        
class UI_RobotLoad (sg.Frame):
    
    _disabled = False

    def __init__ (self, i: int):
        """_summary_ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window for one Robot load parameters
        sg elements like checkbox and buttons are stored in the class to be accessed easily
        Return : sg.Frame
        """       
        self.i = i
        super().__init__(f"Robot {i}", self.__make_layout())

    def __make_layout (self):

        self._input_load = sg.Combo(['0','0.5','1','2'],default_value='0',key=f'-load_robot{self.i}-',size=(5,1))

        self._input_bungee_yellow = sg.Checkbox('Yellow',key=f'-WrapY_robot{self.i}-')
        self._input_bungee_red = sg.Checkbox('Red',key=f'-WrapR_robot{self.i}-')

        self._layout = [
            [ sg.Text("Load :"), sg.Push(), self._input_load , sg.Text("kg") ],
            [ sg.Text("Bungee cords :") ],
            [ self._input_bungee_yellow ],
            [ self._input_bungee_red ]
        ]

        return self._layout
    
    @property
    def disabled (self): # called when : print(disabled)
        return self._disabled
    
    @disabled.setter # called when : disabled = True/False 
    def disabled (self, v: bool):
        """ Give the disabled state v to the entries and combo frome the layout to disable it"""
        self._disabled = v

        self._input_load.update(disabled=v)
        self._input_bungee_yellow.update(disabled=v)
        self._input_bungee_red.update(disabled=v)

    @property
    def setup (self):
        """_summary_
        Returns:
            _type_: array containing the load parameter on the given robot : load weight, bungee cords
        """
        return [
            float(self._input_load.get()),
            1 if self._input_bungee_yellow.get() else 0,
            1 if self._input_bungee_red.get() else 0,
        ]

class UI_Data (sg.Frame):
    
    _disabled = False
    
    def __init__ (self):
        """_summary_ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window for launching measuring sequence and data printing
        sg elements like checkbox and buttons are stored in the class to be accessed easily
        To print collection results from an excel file, select it with "Browse" and store it in python with "OPEN"
        Then show the graphs with buttons below
        Return : sg.Frame
        """         
        super().__init__("Collected Data", self.__make_layout(), expand_x=True)

    def __make_layout (self):
        data_path = os.path.dirname(os.path.realpath(__file__)) + "/data"
        self._btn_start = sg.Button('START SEQUENCE', key='-BTN_start-', button_color='white', size=(25, 2),expand_x=True)
        
        self._input_data = sg.Input(default_text=data_path, key='-data_path-', size=(40, 1), font=("Consolas", 10))
        self.import_xlsx =  sg.FileBrowse("Browse EXCEL",initial_folder=data_path, file_types=(('Excel Files', '*.xlsx'),), key='-browse_xlsx-')
        self.open_xlsx = sg.Button("OPEN", key='-open_xlsx-')
        
        self.trace_selvariables = sg.Button('Trace Selected variables', key='-trace_selvar-', disabled=True, expand_x=True)
        self.trace_samples = sg.Button('Trace Sample collection history', key='-trace_sample-', disabled=True, expand_x=True)
        self.trace_latency = sg.Button('Trace Sample latency distribution', key='-trace_latency-', disabled=True, expand_x=True)

        self._layout = [
            [ self._btn_start ],
            [sg.Frame("", border_width=0, layout = [
                [ self._input_data, self.import_xlsx, self.open_xlsx ],
                [ self.trace_selvariables, self.trace_samples ],
                [ self.trace_latency ]
                ])
            ]
        ]
        return self._layout
    
    @property
    def disabled (self): # called when : print(disabled)
        return self._disabled
    
    @disabled.setter # called when : disabled = True/False 
    def disabled (self, v: bool):
        """ Give the disabled state v to the lauch button to disable it
            Data plot functionality is accessible if a robot is not connected
        """
        self._disabled = v
        self._btn_start.update(disabled=v)
        
    def enable_plot_buttons(self, enable):
        """_summary_
        Updates the state of the plot butons to prevent data plot if no data is already stored in python
        Args:
            enable (bool): True/False to enable/disable buttons
        """
        self.trace_selvariables.update(disabled=not(enable))
        self.trace_samples.update(disabled=not(enable))
        self.trace_latency.update(disabled=not(enable))
    
class UI_Latency(sg.Frame):
    
    _disabled = False
    
    def __init__ (self):
        """_summary_ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window for launching latency measuring sequence
        Containing one single button to launch measuring on the connected robots
        Return : sg.Frame
        """     
        super().__init__("Measure Latency", self.__make_layout(), expand_x= True)

    def __make_layout (self):
        self.start_measure = sg.Button("Start Latency Measure on connected robots", key = '-BTN_latency-')
        
        self.layout = [[self.start_measure]]
        return self.layout
    
    @property
    def disabled (self):
        return self._disabled
    
    @disabled.setter
    def disabled (self, v: bool):
        self._disabled = v
        self.start_measure.update(disabled=v)

class UI_Gripper (sg.Frame):

    _disabled = False
    
    def __init__ (self):
        """_summary_ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window to control the gripper state of a robot
        If robot selected in the Combo is connected, open or close the gripper with buttons
        Return : sg.Frame
        """         
        super().__init__("Gripper", self.__make_layout())

    def __make_layout (self):

        self.robot_choice = sg.Combo(['Robot 1', 'Robot 2', 'Robot 3'], default_value='Robot 2', key='-Rob_choice-')
        self._btn_open = sg.Button('Open', key='-BTN_open_gripper-')
        self._btn_close = sg.Button('Close', key='-BTN_close_gripper-')

        self._layout = [
            [ self.robot_choice, self._btn_open, self._btn_close]
        ]

        return self._layout
    
    @property
    def disabled (self):
        return self._disabled  
    @disabled.setter
    def disabled (self, v: bool):
        self._disabled = v
        self._btn_close.update(disabled=v)
        self._btn_open.update(disabled=v)
        
    @property
    def _robot_choice (self):
        """ Returns the number of the selected robot in the combo for further use """
        target = self.robot_choice.get()
        for i in range(len(self.robot_choice.Values)):
            if target == self.robot_choice.Values[i]:
                return i+1
        return self._disabled

class MainWindow (sg.Window):
    
    def __init__ (self, *args, **kwargs):
        """_summary_ : Class constructor
        With __make_layout, generate the pysimplegui window of the GUI containing all the frames from the other UI class
        Frames are stored in the class variables to be accessed
        Return : sg.Window
        """   
        super().__init__("Data Collection", self.__make_layout(), finalize = True, *args, *kwargs)
    
    def __make_layout (self):

        self.collection_settings = UI_Collection_Settings()
        self.kukatrace = UI_KUKATrace()
        self.robots = [ UI_RobotLoad(i) for i in range(1, 4) ]
        self.latency = UI_Latency()
        self.data = UI_Data()
        self.gripper = UI_Gripper()

        self._layout = [ 
            [ self.collection_settings ],
            [ self.kukatrace ],
            [ self.robots[0], sg.Push(), self.robots[1], sg.Push(), self.robots[2] ],
            [ self.latency, self.gripper],
            [  sg.Push(), self.data, sg.Push() ],
            [ sg.Text("COS0028 - PIE0073, from the work of Bc. Adam Batrla BAT0050, 2024")]
            
        ]
        return self._layout

    
    def get_category (self, cell: int = 1):
        """_summary_
        Give the category of the chosen load for data processing
        Args:
            cell (int, optional): Robot cell number. Defaults to 1.
        Returns:
            _type_: category of the robot load
        """
        if cell - 1 > len(self.robots):
            return -1
        
        robot = self.robots[cell - 1]

        setup = robot.setup # method from UI_robotload
        
        match setup:
            case [0, 0, 0]:
                return 0
            case [0.5, 0, 0]:
                return 1
            case [1, 0, 0]:
                return 2
            case [2, 0, 0]:
                return 3

            case [0, 1, 0]:
                return 4
            case [0.5, 1, 0]:
                return 5
            case [1, 1, 0]:
                return 6
            case [2, 1, 0]:
                return 7

            case [0, 0, 1]:
                return 8
            case [0.5, 0, 1]:
                return 9
            case [1, 0, 1]:
                return 10
            case [2, 0, 1]:
                return 11

            case [0, 1, 1]:
                return 12
            case [0.5, 1, 1]:
                return 13
            case [1, 1, 1]:
                return 14
            case [2, 1, 1]:
                return 15

# UI TEST by launching this file as main
if __name__ == "__main__":
    dataframe = None
    win = MainWindow()
    while True:
        event, values = win.read(100)
        if event == sg.WIN_CLOSED:
            break
        if event == '-open_xlsx-':
            try:
                dataframe = pd.read_excel(values['-data_path-'])
                dataframe['EXEC_TIME_s'] = dataframe['EXEC_TIME']/1000
                sg.popup("Done")
                win.data.enable_plot_buttons(True)
            except Exception as e:
                sg.popup(e)
                win.data.enable_plot_buttons(False)
        if event == '-trace_selvar-':
            if(win.collection_settings._do_tq):
                dataframe.plot(x="EXEC_TIME_s",y=[f"TQ_A{i}" for i in range(1,7,1)], grid=False),plt.ylabel("Motor Torque (N.m)")
            if(win.collection_settings._do_curr):
                dataframe.plot(x="EXEC_TIME_s",y=[f"CURR_A{i}" for i in range(1,7,1)], grid=False),plt.ylabel("Motor Current (%)")
            if(win.collection_settings._do_temp):
                dataframe.plot(x="EXEC_TIME_s",y=[f"TEMP_A{i}" for i in range(1,7,1)], grid=False),plt.ylabel("Motor Temperature (°K)")
            if(win.collection_settings._do_posact):
                dataframe.plot(x="EXEC_TIME_s",y=[f"POS_ACT_A{i}" for i in range(1,7,1)], grid=False),plt.ylabel("Actual Robot position in grid (mm))")
            if(win.collection_settings._do_posreal):
                dataframe.plot(x="EXEC_TIME_s",y=[f"POS_MEAS_A{i}" for i in range(1,7,1)], grid=False),plt.ylabel("Real Robot position in grid (mm))")
            plt.show()
        if event == '-trace_sample-':
            dataframe.plot(x="EXEC_TIME_s",y=["Queue_Read", "Queue_Write"], grid=False),plt.ylabel("Samples")
            plt.xlabel("Collection execution time (s)")
            plt.twinx(), plt.plot(dataframe["EXEC_TIME_s"],dataframe['Total Request Time'], alpha=0.05), plt.ylabel("Request time of the sample (ms)")
            plt.title("Samples in the buffer and red by Python")
            plt.text(2,25,f"Sample time : {dataframe['EXEC_TIME'].diff().median()}")
            plt.show()
        if event == '-trace_latency-':
            dataframe.hist(column='Total Request Time', grid=False, bins=30)
            plt.title("Distribution of the collection time of a sample")
            plt.xlabel(f"Request time (ms) : mean = {dataframe['Total Request Time'].mean().__round__(2)}"),plt.ylabel("Number of samples")
            plt.show()
        if event == '-BTN_open_gripper-':
            print(win.gripper._robot_choice.get)
        if event == '-BTN_start-':
            continue