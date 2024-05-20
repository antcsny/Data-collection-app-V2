import PySimpleGUI as sg
from datetime import datetime
from dateutil import tz
import os

TZ = tz.gettz("Europe/Prague") 

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
    