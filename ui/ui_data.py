import PySimpleGUI as sg
import os

class UI_Data (sg.Frame):
    
    _disabled = False
    
    _do_tq = True
    _do_curr = True
    _do_temp = True
    _do_posact = False
    _do_posreal = False
    
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
        self._btn_start = sg.Button('START SEQUENCE', key='-BTN_start-', button_color='white', size=(15, 2),expand_x=True)
        
        self._input_data = sg.Input(default_text=data_path, key='-data_path-', size=(40, 1), font=("Consolas", 10))
        self.import_xlsx =  sg.FileBrowse("Browse EXCEL",initial_folder=data_path, file_types=(('Excel Files', '*.xlsx'),), key='-browse_xlsx-')
        self.open_xlsx = sg.Button("OPEN", key='-open_xlsx-')
        
        self.trace_selvariables = sg.Button('Trace Selected variables', key='-trace_selvar-', disabled=True, expand_x=True)
        self.trace_samples = sg.Button('Trace Sample collection history', key='-trace_sample-', disabled=True, expand_x=True)
        self.trace_latency = sg.Button('Trace Sample latency distribution', key='-trace_latency-', disabled=True, expand_x=True)
        
        self.do_tq = sg.Checkbox('Motor torque', key='-do_tq-', size=(25, 1), enable_events=True,  default=True)
        self.do_curr = sg.Checkbox('Motor current', key='-do_curr-', size=(25, 1), enable_events=True, default=True)
        self.do_tptr = sg.Checkbox('Motor temperature', key='-do_tprt-', size=(25, 1),enable_events=True, default=True)
        self.do_posact = sg.Checkbox('Robot command position', key='-do_posact-', size=(25, 1), enable_events=True, default=False)
        self.do_posreal = sg.Checkbox('Robot measured position', key='-do_posreal-', size=(25, 1), enable_events=True, default=False)

        self._layout = [
            [ self._btn_start ],
            [ sg.Frame("Quickview of the colelcted data in excel file :", border_width=0, expand_y=True, layout = [
                    [ sg.VPush() ],
                    [ self._input_data, self.import_xlsx, self.open_xlsx ],
                    [ self.trace_selvariables, self.trace_samples ],
                    [ self.trace_latency ],
                    [ sg.VPush() ]
                    ]),
              sg.Frame("Variables to plot :", border_width=0, layout=[
                    [self.do_tq],
                    [self.do_curr],
                    [self.do_tptr],
                    [self.do_posact],
                    [self.do_posreal]
                    ]),
            ],
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
        
    def update_do (self):
        """_summary_
        Update the state of the variables do_XXX if a checkbox is clicked
        """
        self._do_tq = bool(self.do_tq.get())
        self._do_curr = bool(self.do_curr.get())
        self._do_temp = bool(self.do_tptr.get())
        self._do_posact = bool(self.do_posact.get())
        self._do_posreal = bool(self.do_posreal.get())