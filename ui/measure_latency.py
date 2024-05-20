import PySimpleGUI as sg
import numpy as np
import matplotlib.pyplot as plt
import traceback
from time import time_ns

class Measure_latency(sg.Window):
    measuring_delay_done = False
    N = 100
    M = 12
    i = 0
    acc_time_individual_request = None
    acc_time_1 = None
    acc_time_16 = None
    x = None
    x2 = None
    
    def __init__ (self, name: str, *args, **kwargs):
        self.name = name
        super().__init__("Measure Running", self.__make_layout(), *args, *kwargs)

    def __make_layout (self):
        self._layout = [
            [sg.Text('Measuring TCP/IP communication latency...')],
            [sg.Push(), sg.ProgressBar(self.N, orientation='h', size=(20, 20), key='-progress-'), sg.Push()],
            [sg.Text('', key='-bottom_text-')],
        ]
        return self._layout
    
    def measure_latency(self, robot):
        self.acc_time_16 = np.zeros(self.N)
        self.acc_time_1 = np.zeros(self.N)
        self.acc_time_individual_request = np.ones(self.M * self.N) * 12

        self.x = np.arange(0, self.N)
        self.x2 = np.arange(0, self.N, 1/self.M)
        
        try:
            for self.i in range (self.N):
                a = time_ns()
                robot.KUKA_ReadVar("__TAB_1[]")
                b = time_ns()
                time_16 = (b-a) / 1e6
                self.acc_time_16[self.i] = (time_16)
                
                a = time_ns()
                for i in range(self.M):
                    c = time_ns()
                    robot.KUKA_ReadVar(f"__TAB_1[{i}]")
                    d = time_ns()
                    self.acc_time_individual_request[self.i * self.M + i] = (d - c) / 1e6

                b = time_ns()
                time_1 = (b-a) / 1e6
                self.acc_time_1[self.i] = (time_1)

            self.measuring_delay_done = True
            self.write_event_value("--latency-done--", True)

        except Exception as e:
            self.measuring_delay_done = True
            traceback.print_exception(e)

    def _print_results (self):
        plt.figure(figsize=(12.8,6.4))
        plt.subplot(2,3,(1,3))
        plt.plot(self.x2, self.acc_time_individual_request, label="1 var", alpha=0.25)
        plt.plot(self.x, self.acc_time_1, label=f"{self.M} vars using a for loop")
        plt.plot(self.x, self.acc_time_16, label=f"{self.M} vars using an array")
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
        plt.hist(self.acc_time_16, bins=50)
        plt.xlabel("Response time (ms)")
        plt.title(f"Distribution for {self.M} vars array request")

        plt.suptitle(self.name)
        plt.tight_layout()
        plt.pause(0.1)

        # plt.figure()
        # plt.subplot(1,2,1)
        # df = pd.DataFrame({ 
        #     f"Response Time - {self.M} vars, for loop": self.acc_time_1,
        #     f"Response Time - {self.M} vars, array": self.acc_time_16 
        # })
        # df.boxplot()

        # plt.subplot(1,2,2)
        # df = pd.DataFrame({ 
        #     f"Response Time - 1 var": self.acc_time_individual_request,
        # })
        # df.boxplot()
        # plt.show()
 

    def _poll(self):
        event, value = self.read(timeout=10)
        if event == sg.WIN_CLOSED or self.measuring_delay_done:
            self.close()
            self._print_results()
            self.measuring_delay_done = False
            return False
        
        # if event == "--latency-done--":

        self['-progress-'].update(self.i + 1)
        return True