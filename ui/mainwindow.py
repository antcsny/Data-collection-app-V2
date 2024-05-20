import PySimpleGUI as sg

from .ui_colelction_settings import UI_Collection_Settings
from .ui_data import UI_Data
from .ui_gripper import UI_Gripper
from .ui_latency import UI_Latency
from .ui_robot_load import UI_RobotLoad
from .ui_trace import UI_KUKATrace

sg.theme("SystemDefaultForReal")

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
