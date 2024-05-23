import PySimpleGUI as sg
import pandas as pd
import os

class UI_Data (sg.Frame):
    
    _disabled = False
    
    _var_totrace = []
    _do_trace_var = []
    _do_trace_axis = [True, True, True, False, False]
    
    def __init__ (self):
        """ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window for launching measuring sequence and data printing
        sg elements like checkbox and buttons are stored in the class to be accessed easily
        To print collection results from an excel file, select it with "Browse" and store it in python with "OPEN"
        Then show the graphs with buttons below
        Return : sg.Frame
        """         
        super().__init__("Collected Data", self.__make_layout(), expand_x=True)

    def __make_layout (self):
        self._btn_start = sg.Button('START SEQUENCE', key='-BTN_start-', button_color='white', size=(15, 2),expand_x=True)
        
        self.import_data = self.__make_file_browse('1')
        
        self.trace_selvariables = sg.Button('Trace Selected variables', key='-trace_selvar-', disabled=True, expand_x=True)
        self.trace_samples = sg.Button('Trace Sample collection history', key='-trace_sample-', disabled=True, expand_x=True)
        self.trace_latency = sg.Button('Trace Sample latency distribution', key='-trace_latency-', disabled=True, expand_x=True)
        
        self.do_axis = [ sg.Checkbox(f'A{i}', key=f'-do_axis{i}-', enable_events=True, default=True) for i in range(1,7)]
        
        self.var_checkbox = []

        self._layout = [
            [ self._btn_start ],
            [ sg.Frame("Quickview of the colelcted data in excel file :", expand_y=True, layout = [
                    [ sg.VPush() ],
                    [ self.import_data ],
                    [ self.trace_selvariables, self.trace_samples ],
                    [ self.trace_latency ],
                    [ sg.VPush() ],
                    [ sg.Frame("Axis to plot :", border_width=0.5, expand_x=True, layout = [self.do_axis ]) ]
                    ]),
              sg.Frame("Variables to plot :", layout=[ [sg.Col(layout=[], key='-col_var_to_plot-')] ])
            ],
        ]
        return self._layout
    
    def __make_file_browse(self, key:str):
        data_path = os.getcwd() + "/data"
        
        self._input_data = sg.Input(default_text=data_path, key=f'-path_data{key}-', size=(50, 1), font=("Consolas", 10), enable_events=True)
        self.import_xlsx =  sg.FileBrowse("Browse EXCEL",initial_folder=data_path, file_types=(('Excel Files', '*.xlsx'),), key=f'-browse_data{key}-')
        self.open_xlsx = sg.Button("OPEN", key=f'-open_data{key}-')
        return [self._input_data, self.import_xlsx, self.open_xlsx]
    
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
        """
        Updates the state of the plot butons to prevent data plot if no data is already stored in python
        Args:
            enable (bool): True/False to enable/disable buttons
        """
        self.trace_selvariables.update(disabled=not(enable))
        self.trace_samples.update(disabled=not(enable))
        self.trace_latency.update(disabled=not(enable))
        
    def update_do (self):
        """
        Update the state of the variable _do_trace_var if a checkbox is clicked
        """
        for i, _ in enumerate(self._var_totrace):
            self._do_trace_var[i] = bool(self.var_checkbox[i].get())
            
    def get_selected_axis (self):
        i=1
        res = []
        for axis in self.do_axis:
            if axis.get():
                res.append(i)
            i+=1
        return res
        
    def update_layout_on_columns(self, win: sg.Window, columns):
        """
        Updates the window's layout to display new checkboxes
        in order to plot or not the variables from a dataframe
        Args:
            win (sg.Window): window to modify the layout
            columns (list): columns of the dataframe
        Stored in class variable:
            list: list of the collected variables on one robot axis
        """
        for i, _ in enumerate(self._var_totrace):   # reset before displaying
            key = f'-varplot_line{i}-'
            if key in win.key_dict:
                win[key].Widget.destroy()
                del win.AllKeysDict[key]
                del win.AllKeysDict[f'-varplot_cbx{i}-']
        win.read(100)        
        self._var_totrace = []
        self._do_trace_var = []
        self.var_checkbox = []
        i=0
        for col in columns:
            if '_A1' in col: # sorting the variables per axis
                colname = col.rsplit('_A1', 1)[0] 
                self._var_totrace.append(colname)
                self.var_checkbox.append(sg.Checkbox('Motor ' + colname, enable_events=True, default=True, key=f'-varplot_cbx{i}-'))
                win.extend_layout(win['-col_var_to_plot-'], [[sg.pin(sg.Col([[self.var_checkbox[i]]], key=f'-varplot_line{i}-', pad=(1,0.2)))]])
                self._do_trace_var.append(True)
                i+=1
    
