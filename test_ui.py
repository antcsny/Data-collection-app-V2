from ui import MainWindow

import PySimpleGUI as sg
import pandas as pd
import matplotlib.pyplot as plt

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