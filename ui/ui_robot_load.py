import PySimpleGUI as sg

class UI_RobotLoad (sg.Frame):
    
    _disabled = False

    def __init__ (self, i: int):
        """_summary_ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window for one Robot load parameters
        sg elements like checkbox and buttons are stored in the class to be accessed easily
        Return : sg.Frame
        """       
        self.i = i
        super().__init__(f"Robot {i}", self.__make_layout())

    def __make_layout (self):

        self._input_load = sg.Combo(['0','0.5','1','2'],default_value='0',key=f'-load_robot{self.i}-',size=(5,1))

        self._input_bungee_yellow = sg.Checkbox('Yellow',key=f'-WrapY_robot{self.i}-')
        self._input_bungee_red = sg.Checkbox('Red',key=f'-WrapR_robot{self.i}-')

        self._layout = [
            [ sg.Text("Load :"), sg.Push(), self._input_load , sg.Text("kg") ],
            [ sg.Text("Bungee cords :") ],
            [ self._input_bungee_yellow ],
            [ self._input_bungee_red ]
        ]

        return self._layout
    
    @property
    def disabled (self): # called when : print(disabled)
        return self._disabled
    
    @disabled.setter # called when : disabled = True/False 
    def disabled (self, v: bool):
        """ Give the disabled state v to the entries and combo frome the layout to disable it"""
        self._disabled = v

        self._input_load.update(disabled=v)
        self._input_bungee_yellow.update(disabled=v)
        self._input_bungee_red.update(disabled=v)

    @property
    def setup (self):
        """_summary_
        Returns:
            _type_: array containing the load parameter on the given robot : load weight, bungee cords
        """
        return [
            float(self._input_load.get()),
            1 if self._input_bungee_yellow.get() else 0,
            1 if self._input_bungee_red.get() else 0,
        ]