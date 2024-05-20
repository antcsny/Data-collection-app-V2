import PySimpleGUI as sg

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