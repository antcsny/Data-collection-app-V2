from .handler import KUKA_Handler
import xml.etree.ElementTree as et
from time import sleep
import os
import shutil
import re
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path
import pandas as pd

class DatFile:

    sampling: float = 0
    col241: List[float] = []
    traces: List[float] = []
    length: float = 0

    def __init__(self) -> None:
        self.sampling = 0
        self.col241 = []
        self.traces = []
        self.length = 0

class KUKA_Trace:
    """
    This class implements methods to control KUKA.Trace diagnostic tool. It can start or stop the measurement and
    download new_data to desired location.
    """

    # Directory to store the trace file before processing
    temp_folder: Path = Path(os.getcwd(), "temp")

    # The folder of the robot containing the traces
    trace_root: Path = None

    # Translations from German to English
    translations = {
        "Sollposition":                 "Position_Command",
        "Istposition":                  "Position",
        "Positionsschleppfehler":       "Position_Error",
        "Geschwindigkeitsdifferenz":    "Velocity_Error",
        "Motortemperatur":              "Temperature",
        "Istmoment":                    "Torque",
        "Iststrom":                     "Current"
    }

    def __init__(self, rob_instance: KUKA_Handler):
        self.name = None
        self.config = None
        self.rob_instance = rob_instance
        self.enable = False

    def Trace_Enable(self, enable: bool):
        """
        Enables/Disables trace control. If False, all class methods are deactivated and do nothing
        :param enable: Desired state of Trace controlling
        :return:
        """
        self.enable = enable

    def Trace_Config(self, parameters: list):
        """
        Configure trace measurement before starting the trace
        :param parameters - list of trace configuration parameters
        name: New trace name (must be unique)
        configuration: xml file, must be installed in the KRC in folder roboter/TRACE
        duration: trace recording time
        sampling: trace NextGenDrive sampling period
        :return: False, if something goes wrong, True if configuration was successful
        """
        name = parameters[0]
        configuration = parameters[1]
        duration = parameters[2]
        if self.enable:
            config_path = fr'\\{self.rob_instance.ipAddress}\roboter\TRACE\{configuration}.xml'

            self.trace_root = Path(f'\\\\{self.rob_instance.ipAddress}\\roboter\\TRACE\\')

            # try:         # Comented to not modify the xml file
            #     tree = et.parse(config_path)
            #     root = tree.getroot()

            #     for time_element in root.iter('Time'):
            #         time_element.text = duration
            #     tree.write(config_path)


            # except Exception as e:
            #     print(f"XML writing error: {e}")

            if type(name) == str and type(configuration) == str:
                self.rob_instance.KUKA_WriteVar('$TRACE.CONFIG[]', f'"{configuration}.xml"')
                self.rob_instance.KUKA_WriteVar('$TRACE.NAME[]', f'"{name}"')
                self.name = name
                self.config = configuration
            else:
                print('Expected input type: string')
                return False
            new_name_raw = self.rob_instance.KUKA_ReadVar('$TRACE.NAME[]')
            new_name = new_name_raw.decode('UTF-8').strip('"')

            new_config_raw = self.rob_instance.KUKA_ReadVar('$TRACE.CONFIG[]')
            new_config = new_config_raw.decode('UTF-8').strip('"').strip('.xml')
            if new_name != name:
                print(f'Trace name: {name} is unavailable, try different trace name.')
                return False

            if new_config != configuration:
                print(f'Trace configuration: {configuration} does not exist.')
                return False
            print('Trace configuration successful')
            return True
        else:
            return False

    def Trace_Start(self):
        """
        Starts Trace recording and wait for trigger signal
        :return: False, if something goes wrong, True if configuration was successful
        """
        if self.enable:
            self.rob_instance.KUKA_WriteVar('$TRACE.MODE', '#T_START')
            sleep(0.2)
            if self.rob_instance.KUKA_ReadVar('$TRACE.STATE') in [b'#T_WAIT', b'#TRIGGERED']:
                print('Trace is running')
                return True
            else:
                print(f'Error in trace configuration {self.config}')
                return False

    def Trace_Stop(self):
        """
        Stops current recording of trace
        :return: None
        """
        if self.enable:
            self.rob_instance.KUKA_WriteVar('$TRACE.MODE', '#T_STOP')
        if self.rob_instance.KUKA_ReadVar('$TRACE.STATE') in [b'#T_END', b'#T_WRITING']:
            print('Trace stopped')
        else:
            print("Failed to stop the trace")

    def Trace_State(self):
        """
        :return: Returns string containing current state of trace recording
        """
        state_raw = self.rob_instance.KUKA_ReadVar('$TRACE.STATE')
        match state_raw:
            case b'#T_END':
                return 'No recording is currently running.'
            case b'#TRIGGERED':
                return 'Recording in progress'
            case b'#T_WAIT':
                return 'Waiting for the trigger'
            case b'#T_WRITING':
                return 'The recorded new_data are written to the hard drive.'

    def Trace_Ended(self):
        """
        Check if the set trace recording time has already elapsed
        :return: True if the recording ended, False if not
        """
        if self.enable:
            if self.rob_instance.KUKA_ReadVar('$TRACE.STATE') == b'#T_END':
                return True
            else:
                return False

    def Trace_Download(self):
        

        result = self.read_traces(self.name)

        return result

    def translate (self, value: str) -> str:

        if value in self.translations:
            return self.translations[value]
        
        return value

    def copy_to_local (self, pairs: List[List[Path]], name: str):

        src_folder = None
        if type (self.trace_root) == str :
            src_folder = self.trace_root
        else:
            src_folder = self.trace_root.absolute()

        self.dest_folder = self.temp_folder.joinpath(name).absolute()

        if not self.dest_folder.exists():
            self.dest_folder.mkdir(parents=True)

        for pair in pairs:
            for file in pair:
                src = None
                if type(src_folder) == str:
                    src = src_folder + str(file)
                else:
                    src = src_folder.joinpath(file)
                dest = self.dest_folder.joinpath(file)
                shutil.copyfile(src, dest)
                src.unlink()

    def find_pairs (self, name: str):

        extensions = ['.dat', '.r64', ".trc"]
        file_names = [
            "KRCIpo",
            *[ f"NextGenDrive#{i}" for i in range(1,7) ]
        ]
        files = []

        for file_name in file_names:
            
            path = Path(f'{name}_{file_name}')
            files.append([ path.with_suffix(s) for s in extensions ])

        return files

    def read_dat (self, dat: Path, suffix: str = "") -> DatFile:
        
        out = DatFile()

        with open(dat, "r") as dat_file:

            config = [ line.strip() for line in dat_file.readlines() ]

            inChannel = False
            isZeit = False

            for line in config:

                if line == "#BEGINCHANNELHEADER":
                    inChannel = True
                    continue

                if line == "#ENDCHANNELHEADER":
                    inChannel = False
                    continue

                if not inChannel:
                    continue

                code, value = line.split(",")

                if isZeit:
                    if code == "241":
                        out.sampling = float(value)
                        isZeit = False
                    continue

                match code:
                    case "200":                        
                        if value == "Zeit":
                            isZeit = True
                            continue
                        
                        out.traces.append(self.translate(value) + suffix)

                    case "220":
                        l = int(value)
                        if out.length == 0:
                            out.length = l

                    case "241":                        
                        out.col241.append(float(value))

        return out

    def convert_r64 (self, r64: Path, dat: DatFile) -> Dict[str, List[float]]:

        out: Dict[str, List[float]] = {}

        for col in dat.traces:
            out[col] = []

        N = len(dat.traces)

        with open(r64, "rb") as file:

            samples = np.fromfile(file, dtype='float64')
            length = len(samples) // N

            for i in range(length):
                for n in range(N):
                    col = dat.traces[n]
                    out[col].append(samples[i * N + n] * dat.col241[n])

        return out
    
    def linear_interpolation (self, data: List[float], ratio: int = 1):
        if ratio == 1:
            return data
        
        data_len = len(data)
        neo_len = data_len * ratio

        neo = np.zeros(neo_len)
        neo[::ratio] = data

        for i in range(1,neo_len):
            # Skip existing data points
            if i % ratio == 0:
                continue
            
            k = i // ratio
            if (k + 1) >= data_len:
                neo[i] = data[k]
                continue

            a = data[k+1] - data[k]
            b = data[k+1] - a

            neo[i] = (k / ratio) * a + b

        return neo            

    def read_traces (self, name: str):

        pairs = self.find_pairs(name)
        self.copy_to_local(pairs, name)
        self.copy_to_local([[f'{name}_PROG.TXT']], name)

        data: List[Tuple[DatFile, Dict[str, List[float]]]] = []

        for pair in pairs:

            dat_path = self.dest_folder.joinpath(pair[0])

            suffix = ""
            if '#' in dat_path.stem:
                n = re.search(r'#(.)', dat_path.stem).group(1)
                suffix = f'_A{n}'

            dat = self.read_dat(dat_path, suffix)

            r64_path = self.dest_folder.joinpath(pair[1])
            r64 = self.convert_r64(r64_path, dat)

            data.append((dat, r64))

        min_sampling = data[0][0].sampling
        for d in data:
            min_sampling = min(d[0].sampling, min_sampling)

        min_length = 12e9
        for d in data:
            ratio = int(d[0].sampling // min_sampling)
            min_length = min(d[0].length * ratio, min_length)

        length = min_length

        dataframe = pd.DataFrame()

        for d in data:
            dat = d[0]
            ratio = int(dat.sampling // min_sampling)

            values = d[1]

            for col in values:

                if ratio > 1:
                    
                    if "AnalogOut" in col:
                        # Step interpolation
                        temp = np.zeros(len(values[col]) * ratio)
                        for i in range(ratio):
                            temp[i::ratio] = values[col]
                        dataframe[col] = temp[:length]
                    else:
                        # Linear interpolation
                        dataframe[col] = self.linear_interpolation(values[col], ratio)[:length]

                else:
                    dataframe[col] = np.float64(values[col])[:length]

        T = len(dataframe[dataframe.columns[0]])
        dataframe["Sample_time"] = np.arange(T) * min_sampling

        return dataframe[[dataframe.columns[-1], *dataframe.columns[:-1]]]
