import PySimpleGUI as sg
import os
import pandas as pd
import matplotlib.pyplot as plt


sg.theme("SystemDefaultForReal")

class MainWindow (sg.Window):
    
    dataframe = []
    dataframe.append(None)
    dataframe.append(None)
    # Flags to enable the plot of variables in datasets : torque, curent, temperature, command position, measured position
    _do_trace = [True, True, True, False, False]
    
    def __init__ (self, *args, **kwargs):
        """
        With __make_layout, generate the pysimplegui window of the GUI
        Return : sg.Window
        """   
        super().__init__("Data Plot", self.__make_layout(), finalize = True, *args, *kwargs)
    
    def __make_layout (self):

        # plot des variables qu'on veut : combo selon les colonnes du dataframe ouvert
        # plot des données d'une seule variable sur un seul axe
        self.data = self.def_file_browse('data1')
        self.data2 = self.def_file_browse('data2')
        
        self.do_tq = sg.Checkbox('Motor torque', key='-do_tq-', size=(25, 1), enable_events=True,  default=True)
        self.do_curr = sg.Checkbox('Motor current', key='-do_curr-', size=(25, 1), enable_events=True, default=True)
        self.do_tptr = sg.Checkbox('Motor temperature', key='-do_tprt-', size=(25, 1),enable_events=True, default=True)
        self.do_posact = sg.Checkbox('Robot command position', key='-do_posact-', size=(25, 1), enable_events=True, default=False)
        self.do_posreal = sg.Checkbox('Robot measured position', key='-do_posreal-', size=(25, 1), enable_events=True, default=False)
        self.do_axis = [ sg.Checkbox(f'A{i}', key=f'-do_axis{i}-', enable_events=True, default=True) for i in range(1,7)]

        self._layout = [ 
            [ self.data ],
            [ self.data2 ],
            [ sg.Frame("Variables to plot :", border_width=0, layout=[
                    [self.do_tq],
                    [self.do_curr],
                    [self.do_tptr],
                    [self.do_posact],
                    [self.do_posreal]
                    ]),
            ],
            [ sg.Text('Axis to plot :'), *self.do_axis ],
            [ sg.Button('Trace Selected variables', key='-trace_selvar-', disabled=False, expand_x=True) ]
        ]
        return self._layout
    
    def def_file_browse(self, key:str):
        data_path = os.path.dirname(os.path.realpath(__file__)) + "/data"
        self._input_data = sg.Input(default_text=data_path, key=f'-path_{key}-', size=(130, 1), font=("Consolas", 10))
        self.import_xlsx =  sg.FileBrowse("Browse EXCEL",initial_folder=data_path, file_types=(('Excel Files', '*.xlsx'),), key=f'-browse_{key}-')
        self.open_xlsx = sg.Button("OPEN", key=f'-open_{key}-')
        return [self._input_data, self.import_xlsx, self.open_xlsx]
    
    def open_xlsx_file (self, path: str, dfnb:int):
        """Tries to load a .xslx file collected from the system variables

        Args:
            path (str): The path to the file to open
        """        
        try:
            self.dataframe[dfnb-1] = pd.read_excel(path)
            if 'TRACE' in path :
                self.dataframe[dfnb-1]['Sample_time_s'] = self.dataframe[dfnb-1]['Sample']/1000
                self.enable_var_buttons(True, 'TRACE')
            else:
                self.dataframe[dfnb-1]['Sample_time_s'] = self.dataframe[dfnb-1]['Sample_time']/1000
                self.enable_var_buttons(True, 'default')
            self.update_do()
            self.data_col = self.dataframe[dfnb-1].columns
        except Exception as e:
            self.enable_var_buttons(False)
            sg.popup(e)
            
    def update_do (self):
        """_summary_
        Update the state of the variables do_XXX if a checkbox is clicked
        """
        i=0
        for checkbox in [self.do_tq, self.do_curr, self.do_tptr, self.do_posact, self.do_posreal]:
            self._do_trace[i] = bool(checkbox.get()) and checkbox.Disabled == False
            checkbox.update(value = self._do_trace[i])
            i+=1
        
    def trace_selected_variables (self, dfnb:int):
        plt.close('all')
        a = self.get_selected_axis()
        if(self._do_trace[0]):
            self.dataframe[dfnb-1].plot(x="Sample_time_s",y=[f"Torque_A{i}" for i in a], grid=True),plt.ylabel("Motor Torque (N.m)")
        if(self._do_trace[1]):
            self.dataframe[dfnb-1].plot(x="Sample_time_s",y=[f"Current_A{i}" for i in a], grid=True),plt.ylabel("Motor Current (%)")
        if(self._do_trace[2]):
            self.dataframe[dfnb-1].plot(x="Sample_time_s",y=[f"Temperature_A{i}" for i in a], grid=True),plt.ylabel("Motor Temperature (°K)")
        if(self._do_trace[3]):
            self.dataframe[dfnb-1].plot(x="Sample_time_s",y=[f"Position_Command_A{i}" for i in a], grid=True),plt.ylabel("Robot command position in grid (mm))")
        if(self._do_trace[4]):
            self.dataframe[dfnb-1].plot(x="Sample_time_s",y=[f"Position_A{i}" for i in a], grid=True),plt.ylabel("Real Robot position in grid (mm))")
        plt.pause(0.1) # Alternative to plt.show() that is not blocking
        
    def get_selected_axis (self):
        i=1
        res = []
        for axis in self.do_axis:
            if axis.get():
                res.append(i)
            i+=1
        return res
    
    def enable_var_buttons (self, enable:bool, case:str = ''):
        e = not(enable and (case == 'TRACE' or case == 'default'))
        f = not(enable and case != 'TRACE')
        self.do_tq.update(disabled=e)
        self.do_curr.update(disabled=e)
        self.do_tptr.update(disabled=f)
        self.do_posact.update(disabled=f)
        self.do_posreal.update(disabled=f)

window = MainWindow()
while True:
    event, values = window.read(100)
    if event == sg.WIN_CLOSED:
        break
    if event == '-open_data1-':
        window.open_xlsx_file(values['-path_data1-'], 1)
    if event == '-open_data2-':
        window.open_xlsx_file(values['-path_data2-'], 2)
    if '-do_' in event:
        window.update_do()
    if event == '-trace_selvar-':
        window.trace_selected_variables(1)
    
window.close()