# Python Librairies
import PySimpleGUI as sg
import pandas as pd
import matplotlib.pyplot as plt
import threading as th
from typing import List
import traceback

# User Librairies
from ui import MainWindow
from kuka import KUKA_Handler
from measure import Measure_robot, Measure_latency
from classes_functions import open_help

trace_enable = False
sys_var_enable = True

# GLOBAL VARIABLES
data_buffer = {}
collecting_data_done = False
reading_data_done = False
reading_progress = 0
measuring_delay_done = False
delay_progress = 0
abort_process = False
sync_done = 0
sync_number = 0
sync_sem = th.Semaphore(0)


window = MainWindow()
window_latency = []
robot_windows = []

robot_handlers: List[KUKA_Handler] = [ None ] * 3

######################################### FUNCTION DECLARATION ###################################################

def connect_robot_cell (window: MainWindow, cell: int):
    
    handler = KUKA_Handler(f"192.168.1.15{cell}", 7000)

    try:
        ok = handler.KUKA_Open()
        if not ok:
            window.write_event_value(f"-rob_errored:{cell}-", None)
            return
    except Exception as e:
        traceback.print_exception(e)
        sg.popup_ok("\n".join(traceback.format_exception(e)))
        window.write_event_value(f"-rob_errored:{cell}-", None)
        return

    robot_handlers[cell - 1] = handler    
    window.write_event_value(f"-rob_connected:{cell}-", None)

def update_disabled_ui (window: MainWindow):
    
    disabled = True
    for i in range(len(robot_handlers)):
        r = robot_handlers[i]
        disabled = disabled and (r is None)
        window.robots[i].disabled = (r is None)

    window.collection_settings.disabled = disabled
    window.kukatrace.disabled = disabled
    window.latency.disabled = disabled
    window.gripper.disabled = disabled
    window.data.disabled = disabled
            
    window.collection_settings.update_robot_buttons()


def done ():
    global sync_done
    global sync_number
    global sync_sem
    sync_done += 1
    if sync_done == sync_number:
        sync_done = 0
        sync_sem.release(sync_number)

################################################## MAIN PROGRAM ##################################################

update_disabled_ui(window)

plt.figure()
plt.close()  # To adjust DPI of GUI

while True:
    event, values = window.read(timeout=1)

    ### Unconditionnal updates ###
    
    ######################## Core Event ########################
    if event in (sg.WINDOW_CLOSE_ATTEMPTED_EVENT, sg.WIN_CLOSED, 'Exit'):
        for r in robot_handlers:
            if r is not None:
                r.KUKA_Close()
        plt.close('all')
        break
    
    if event == '-BTN_help-':
        open_help()
        
    if event == '-equal_iter-':
        for i in range(1, 7):
            window[f'num_of_iter{i}'].update(value=values['num_of_iter1'])
            
    if event == '-BTN_start-':
        
        if not window.collection_settings.check_configuration():
            continue

        file_path = values["-user_path-"] + "/" + values["-dataset_name-"]

        robot_windows = [ ]
        for i in range(len(robot_handlers)):
            r = robot_handlers[i]
            if r is not None:
                robot_windows.append(Measure_robot(r, i + 1, file_path))

        sync_number = len(robot_windows)
        sync_sem = th.Semaphore(0)
        
        sync_done = 0
        A_iter = [ values[f'num_of_iter{i}'] for i in range(1,7) ]
        speed = window.collection_settings.speed
        sampling = values["-Sys_sampling-"]
        trace_sampling = values["-Trace_config-"]

        for r in robot_windows:
            
            r._poll()
            t = th.Thread(
                target=r.measure_sequence, 
                args=[ A_iter, speed, sampling, trace_sampling, window.get_category(r.cell), sync_sem, done ], 
                daemon=False)
            t.start()

        sync_sem.release(sync_number)

    for i in range(len(window_latency)):
        w = window_latency[i]
        if w is not None:
            if w._poll() is False:
                window_latency[i] = None 

    for i in range(len(robot_windows)):
        win = robot_windows[i]
        
        # Window closed
        if win is None:
            continue

        # Window closed
        if not win._poll():
            # Récupérer les données
            
            robot_windows[i] = None    
            continue
    
    if event == "-dataset_auto-name-":
        window.collection_settings._input_dataset_name.update(value=window.collection_settings.now())

    if event == '-BTN_latency-':
        try:
            window_latency = []
            for i in range(len(robot_handlers)):
                r = robot_handlers[i]
                if r is not None:
                    w = Measure_latency(f"Latency measurement for Robot {i + 1}")
                    w._poll()
                    window_latency.append(w)
                    t = th.Thread(target=w.measure_latency, args=[r], daemon=False)
                    t.start()

        except Exception as e:
            sg.popup_ok(e)

    if event == '-doconst_speed-':
            window.collection_settings.update_speed_entry()

    if 'do' in event:
            window.collection_settings.update_do()
    ######################## Robot Selector Events #################
    if "rob_select" in event:
        cell = int(event.split(':')[1][:-1])

        if robot_handlers[cell - 1] is not None:
            print(f"Trying to disconnect from robot {cell}")
            window.collection_settings.set_robot_connected(cell - 1, False)
            robot_handlers[cell - 1].KUKA_Close()
            robot_handlers[cell - 1] = None
            update_disabled_ui(window)
            continue

        update_disabled_ui(window)
        print(f"Trying to connect to robot {cell}")
        window.perform_long_operation(lambda: connect_robot_cell(window, cell), "-connect-call-end-")

    if "rob_connected" in event:
        cell = int(event.split(':')[1][:-1])
        window.collection_settings.set_robot_connected(cell - 1, True)
        update_disabled_ui(window)

    if "rob_errored" in event:
        cell = int(event.split(':')[1][:-1])
        window.collection_settings.set_robot_connected(cell - 1, False, True)
        update_disabled_ui(window)

    ######################## Gripper Events ########################
    if event == '-BTN_open_gripper-':
        if robot_handlers[window.gripper._robot_choice - 1] is not None:
            robot_handlers[window.gripper._robot_choice - 1].KUKA_WriteVar('PyOPEN_GRIPPER', True)
            window.gripper._btn_open.update(disabled=True)
            window.gripper._btn_close.update(disabled=False)

    if event == '-BTN_close_gripper-':
        if robot_handlers[window.gripper._robot_choice - 1] is not None:
            robot_handlers[window.gripper._robot_choice - 1].KUKA_WriteVar('PyCLOSE_GRIPPER', True)
            window.gripper._btn_open.update(disabled=False)
            window.gripper._btn_close.update(disabled=True)
            
    ######################## Import Excel Trace ########################
    if event == '-open_xlsx-':
            try:
                dataframe = pd.read_excel(values['-data_path-'])
                dataframe['Sample_time_s'] = dataframe['Sample_time']/1000
                sg.popup("Done")
                window.data.enable_plot_buttons(True)
            except Exception as e:
                sg.popup(e)
                window.data.enable_plot_buttons(False)
                
    if event == '-trace_selvar-':
        if(window.collection_settings._do_tq):
            dataframe.plot(x="Sample_time_s",y=[f"Torque_A{i}" for i in range(1,7,1)], grid=True),plt.ylabel("Motor Torque (N.m)")
        if(window.collection_settings._do_curr):
            dataframe.plot(x="Sample_time_s",y=[f"Current_A{i}" for i in range(1,7,1)], grid=True),plt.ylabel("Motor Current (%)")
        if(window.collection_settings._do_temp):
            dataframe.plot(x="Sample_time_s",y=[f"Temperature_A{i}" for i in range(1,7,1)], grid=True),plt.ylabel("Motor Temperature (°K)")
        if(window.collection_settings._do_posact):
            dataframe.plot(x="Sample_time_s",y=[f"Command_A{i}" for i in range(1,7,1)], grid=True),plt.ylabel("Robot command position in grid (mm))")
        if(window.collection_settings._do_posreal):
            dataframe.plot(x="Sample_time_s",y=[f"Position_A{i}" for i in range(1,7,1)], grid=True),plt.ylabel("Real Robot position in grid (mm))")
        plt.show()
    
    if event == '-trace_sample-':
        dataframe.plot(x="Sample_time_s",y=["Queue_Read", "Queue_Write"], grid=True),plt.ylabel("Samples")
        plt.xlabel("Collection execution time (s)")
        plt.twinx(), plt.plot(dataframe["Sample_time_s"],dataframe['Read_time'], alpha=0.05), plt.ylabel("Request time of the sample (ms)")
        plt.title("Samples in the buffer and red by Python")
        plt.text(10,10,f"Mean ample time : {dataframe['Sample_time'].diff().mean()}")
        plt.show()
        
    if event == '-trace_latency-':
        dataframe.hist(column='Read_time', grid=True, bins=30)
        plt.title("Distribution of the collection time of a sample")
        plt.xlabel(f"Request time (ms) : mean = {dataframe['Read_time'].mean().__round__(2)}"),plt.ylabel("Number of samples")
        plt.show()

for r in robot_handlers:
    if r is not None:
        r.KUKA_Close()

window.close()
