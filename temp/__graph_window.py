import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from threading import Semaphore

class CollectionGraphWindow (sg.Window):
    
    lock = Semaphore(1)

    def __init__(self, cell: int):
        self.cell = cell
        self._title = sg.Text(f'Robot {self.cell}', key="-TITLE-", font='Helvetica 20')
        self._subtitle = sg.Text("Collecting sample n°...", key="Subtitle")
        self._canvas_elem = sg.Canvas(size=(480,360), key="-CANVAS-")
        self._status = sg.Text("",key="-colstatus-",text_color="#000", font="Helvetica 15")
        self._exit = sg.Button("Exit", key='-colexit-',font="Helvetica 11", size=(15,1))

        _graph_layout = [
            [ sg.Push(), self._title, sg.Push() ],
            [ sg.Push(), self._subtitle, sg.Push() ],
            [ self._canvas_elem ],
            [ sg.Push(), self._status, sg.Push() ],
            [ sg.Push(), self._exit, sg.Push() ]
        ]

        self._data_buffer = []
        self._data_latency = []

        self._s = 0
        super().__init__(f'Robot {cell}', _graph_layout, finalize=True)
        
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
        

    def add (self, buffer: int, latency: float):
        self.lock.acquire()
        self._data_buffer.append(buffer)
        self._data_latency.append(latency)
        self._s += 1
        self.lock.release()
        
    def redraw (self):
        self.lock.acquire()
        a = [*self._data_buffer]
        b = [*self._data_latency]
        self.lock.release()
        self._ax.cla()
        self._ax.set_xlabel("Sample")
        self._ax.set_ylabel("Number of buffered values")
        self._ax.grid()
        self._ax.plot(range(len(a)), a)
        
        self._ay.cla()
        self._ay.set_xlabel("Sample")
        self._ay.set_ylabel("Network latency")
        self._ay.grid()
        self._ay.plot(range(len(b)), b)

        self._fig_agg.draw()
        self._subtitle.update(f"Collecting sample n°{self._s}")

if __name__ == "__main__":
    import math
    import random
    import time
    win = CollectionGraphWindow(1)
    win.read(timeout=100)

    for i in range(200):
        event, value = win.read(timeout=10)

        if event == sg.WIN_CLOSED:
            exit(0)

        win.add(math.sin(2 * math.pi * 0.1 * i), random.randint(1,100) / 10)
        time.sleep(1/30)


    win.close()
