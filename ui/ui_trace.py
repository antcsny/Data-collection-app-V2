import PySimpleGUI as sg

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

        self._sampling_rate = sg.Combo(['12_ms','12_ms_v2','4_ms_v2'], key='-Trace_config-', default_value='12_ms_v2', size=(20, 1))
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