import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from threading import Semaphore

class CollectionGraphWindow (sg.Window):
    
    lock = Semaphore(1)
    enable = True

    def __init__(self, cell: int, enable: True):
        """ : Class constructor
        With __make_layout, generate a pysimplegui window to be shown when a colelction sequence on a robot is lauched
        give a dynamic view of the robot buffer fill level and sample latency with plot
        shows when collection is done without closing the plots, press exit to close
        Return : sg.Window
        """
        self.cell = cell

        self._data_buffer = []
        self._data_latency = []

        self._s = 0
        self.enable = enable
        
        super().__init__(f'Robot {cell}', self.__make_layout(), finalize=True)
        
        # Canvas settings enabled if system variables are collected
        if self.enable:
            self._canvas = self._canvas_elem.TKCanvas
            self._figure: Figure = Figure()
            self._ax = self._figure.add_subplot(2, 1, 1)
            self._ay = self._figure.add_subplot(2, 1, 2)

            self._ax.set_xlabel("Sample")
            self._ax.set_ylabel("Number of buffered values")
            self._ax.grid()

            self._ay.set_xlabel("Sample")
            self._ay.set_ylabel("Network latency (ms)")
            self._ay.grid()

            self._fig_agg = FigureCanvasTkAgg(self._figure, self._canvas)
            self._fig_agg.draw()
            self._fig_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        
    def __make_layout (self):
        self._title = sg.Text(f'Robot {self.cell}', key="-TITLE-", font='Helvetica 20', size=(20,3), justification='center')
        self._subtitle = sg.Text("Collecting Data ...", key="Subtitle")
        if self.enable:
            self._canvas_elem = sg.Canvas(size=(480,360), key="-CANVAS-")
        else:
            self._canvas_elem = None
        self._status = sg.Text("",key="-colstatus-", text_color="#000", font="Helvetica 15")
        self._exit = sg.Button("Exit", key='-colexit-',font="Helvetica 11", size=(15,1),button_color='#F0F0F0')
        
        layout = [
            [ sg.Push(), self._title, sg.Push() ],
            [ sg.Push(), self._subtitle, sg.Push() ],
        ]
        if self.enable:
            layout.append([ self._canvas_elem ])
        layout.append([ sg.Push(), self._status, sg.Push() ])
        layout.append([ sg.Push(), self._exit, sg.Push() ])
        return layout
        
    def add (self, buffer: int, latency: float):
        """
        Adds a data point to the dynamic plot
        Args:
            buffer (int): Sample_number - sample_read
            latency (float): sample collection latency (ms)
        """
        self.lock.acquire()
        self._data_buffer.append(buffer)
        self._data_latency.append(latency)
        self._s += 1
        self.lock.release()
        
    def redraw (self):
        """
        Redraw the dynamic plot on the window to integrate new values
        """
        self.lock.acquire()
        a = [*self._data_buffer]
        b = [*self._data_latency]
        self.lock.release()
        # Sample plot redraw
        self._ax.cla()
        self._ax.set_xlabel("Sample")
        self._ax.set_ylabel("Number of buffered values")
        self._ax.grid()
        self._ax.plot(range(len(a)), a)
        # Latency plot redraw
        self._ay.cla()
        self._ay.set_xlabel("Sample")
        self._ay.set_ylabel("Network latency")
        self._ay.grid()
        self._ay.plot(range(len(b)), b)

        self._figure.tight_layout()

        self._fig_agg.draw()
        self._subtitle.update(f"Collecting sample n°{self._s}")