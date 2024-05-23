import PySimpleGUI as sg
import numpy as np
import matplotlib.pyplot as plt
import traceback
from time import time_ns

class Measure_latency(sg.Window):
    """Measurement window for network latency 
    """    

    # Flag to close the progress window when done
    measuring_delay_done = False

    # Test parameters
    N = 100             # Number of requests
    M = 12              # Size of the array
    i = 0

    # Buffers
    acc_time_individual_request = None
    acc_time_1 = None
    acc_time_M = None

    # X-Axis
    x = None
    x2 = None
    
    def __init__ (self, name: str, *args, **kwargs):
        """ : Class constructor
        With __make_layout, generate a pysimplegui window to be shown in parallel 
        when a latency measure sequence on a robot is lauched 
        plots latency graphs for single variable and an array of a given size
        Return : sg.Window
        """
        self.name = name
        super().__init__("Measure Running", self.__make_layout(), *args, *kwargs)

    def __make_layout (self):
        """Creates this window Layout

        Returns:
            List[]: This window layout
        """        

        self._layout = [
            [sg.Text('Measuring TCP/IP communication latency...')],
            [sg.Push(), sg.ProgressBar(self.N, orientation='h', size=(20, 20), key='-progress-'), sg.Push()],
            [sg.Text('', key='-bottom_text-')],
        ]
        return self._layout
    
    def measure_latency(self, robot):
        """Runs a latency measurement
        Args:
            robot (KUKA_Handler): The robot handler
        """        

        print("Measuring latency with " + str(robot.ipAddress))

        # Preparing the buffers
        self.acc_time_M = np.zeros(self.N)
        self.acc_time_1 = np.zeros(self.N)
        self.acc_time_individual_request = np.ones(self.M * self.N) * 12

        # Preparing the graphs x axis
        self.x = np.arange(0, self.N)
        self.x2 = np.arange(0, self.N, 1/self.M)
        
        try:
            for self.i in range (self.N):

                # Reading a whole array at once
                a = time_ns()
                robot.KUKA_ReadVar("__TAB_1[]")
                b = time_ns()
                time_16 = (b-a) / 1e6
                # Recording the request time
                self.acc_time_M[self.i] = (time_16)
                
                # Reading an array, one index at a time
                a = time_ns()
                for i in range(self.M):
                    c = time_ns()
                    robot.KUKA_ReadVar(f"__TAB_1[{i}]")
                    d = time_ns()
                    # Recording the individual request time
                    self.acc_time_individual_request[self.i * self.M + i] = (d - c) / 1e6

                b = time_ns()
                time_1 = (b-a) / 1e6
                # Recording the whole array request time
                self.acc_time_1[self.i] = (time_1)

            self.measuring_delay_done = True
            self.write_event_value("--latency-done--", True)

        except Exception as e:
            self.measuring_delay_done = True
            traceback.print_exception(e)

    def _print_results (self):
        """Shows the results of the latency measurement to the user using 
        `matplotlib`
        """        

        plt.figure(figsize=(12.8,6.4))
        plt.subplot(2,3,(1,3))
        plt.plot(self.x2, self.acc_time_individual_request, label="1 var", alpha=0.25)
        plt.plot(self.x, self.acc_time_1, label=f"{self.M} vars using a for loop")
        plt.plot(self.x, self.acc_time_M, label=f"{self.M} vars using an array")
        plt.xlabel("Sample"), plt.ylabel("Response Time (ms)"), plt.legend()

        plt.subplot(2,3,4)
        plt.hist(self.acc_time_individual_request, bins=50)
        plt.xlabel("Response time (ms)")
        plt.title("Distribution for individual requests")

        plt.subplot(2,3,5)
        plt.hist(self.acc_time_1, bins=50)
        plt.xlabel("Response time (ms)")
        plt.title(f"Distribution for {self.M} vars request using a for loop")

        plt.subplot(2,3,6)
        plt.hist(self.acc_time_M, bins=50)
        plt.xlabel("Response time (ms)")
        plt.title(f"Distribution for {self.M} vars array request")

        plt.suptitle(self.name)
        plt.tight_layout()
        plt.pause(0.1)
 

    def _poll(self):
        """Updates this window. MUST BE CALLED BY THE MAIN THREAD.

        Returns:
            bool: This window is still opened
        """ 

        event, value = self.read(timeout=10)

        if event == sg.WIN_CLOSED or self.measuring_delay_done:
            self.close()
            self._print_results()
            self.measuring_delay_done = False
            return False
        
        self['-progress-'].update(self.i + 1)
        return True