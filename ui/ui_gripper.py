import PySimpleGUI as sg

class UI_Gripper (sg.Frame):

    _disabled = False
    
    def __init__ (self):
        """_summary_ : Class constructor
        With __make_layout, generate a pysimplegui frame to be integrated in the main window to control the gripper state of a robot
        If robot selected in the Combo is connected, open or close the gripper with buttons
        Return : sg.Frame
        """         
        super().__init__("Gripper", self.__make_layout())

    def __make_layout (self):

        self.robot_choice = sg.Combo(['Robot 1', 'Robot 2', 'Robot 3'], default_value='Robot 2', key='-Rob_choice-')
        self._btn_open = sg.Button('Open', key='-BTN_open_gripper-')
        self._btn_close = sg.Button('Close', key='-BTN_close_gripper-')

        self._layout = [
            [ self.robot_choice, self._btn_open, self._btn_close]
        ]

        return self._layout
    
    @property
    def disabled (self):
        return self._disabled  
    @disabled.setter
    def disabled (self, v: bool):
        self._disabled = v
        self._btn_close.update(disabled=v)
        self._btn_open.update(disabled=v)
        
    @property
    def _robot_choice (self):
        """ Returns the number of the selected robot in the combo for further use """
        target = self.robot_choice.get()
        for i in range(len(self.robot_choice.Values)):
            if target == self.robot_choice.Values[i]:
                return i+1
        return self._disabled