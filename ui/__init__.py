# import python classes from the folder ui

from .ui_collection_settings import UI_Collection_Settings
from .ui_data import UI_Data
from .ui_gripper import UI_Gripper
from .ui_latency import UI_Latency
from .ui_robot_load import UI_RobotLoad
from .ui_trace import UI_KUKATrace
from .mainwindow import MainWindow
from .graph_window import CollectionGraphWindow
from .measure_latency import Measure_latency
from .measure_robot import Measure_robot

print("Loaded UI classes")