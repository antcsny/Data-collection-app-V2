from .handler import KUKA_Handler
import xml.etree.ElementTree as et
from time import sleep
import os
import re
import numpy as np

class KUKA_Trace:
    """
    This class implements methods to control KUKA.Trace diagnostic tool. It can start or stop the measurement and
    download new_data to desired location.
    """

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

    def Trace_Download(self, directory, delete_rob_file):
        """
        Downloads the .r64 and .dat files with previously set self.name from KRC's shared folder IP/roboter/TRACE into
        new folder.
        :param directory: directory of trace new_data folder
        :param delete_rob_file: If true, system will delete trace recording from KRC.
        :return:
        """
        if self.enable:
            extensions = ['.dat', '.r64', '.trc']
            file_paths = []
            axis_paths = []

            if self.name is not None:
                for extension in extensions:
                    axis_paths.append(fr"\\{self.rob_instance.ipAddress}\roboter\TRACE\{self.name}_KRCIpo{extension}")
                    for axis in range(1, 7):
                        file_paths.append(
                            fr"\\{self.rob_instance.ipAddress}\roboter\TRACE\{self.name}_NextGenDrive#{axis}{extension}")
                file_paths.append(fr"\\{self.rob_instance.ipAddress}\roboter\TRACE\{self.name}_PROG.TXT")

            else:
                print('Configure Trace before downloading')
                return False
            file_path = directory + rf'\{self.name}.csv'

            data_buffer = self.r64_converter(file_paths)
            active_axis_raw = self.r64_converter(axis_paths)
            active_axis_raw['Main Category'] = [0] * len(active_axis_raw['AnalogOut1'])
            for axis in range(1,7):
                active_axis_raw[f'A{axis}'] = [0]*len(active_axis_raw['AnalogOut1'])
            for sample in range(0,len(active_axis_raw['AnalogOut1'])):
                axis_number = str(int(active_axis_raw['AnalogOut1'][sample]))
                if axis_number != '0':
                    active_axis_raw[f'A{axis_number}'][sample] = 1
                else:
                    active_axis_raw['Main Category'][sample] = -1

            del active_axis_raw['Sample']
            del active_axis_raw['AnalogOut1']
            result = data_buffer | active_axis_raw

            lengths = [len(values) for values in result.values()]
            min_data_length = min(lengths)

            for key in result.keys():
                result[key] = result[key][:min_data_length-1]

            if delete_rob_file:
                file_paths = file_paths + axis_paths
                for file_path in file_paths:
                    os.remove(file_path)
            return result
        
    def r64_converter(self, file_names):
        data = {}
        for file in file_names:
            if '#' in file:
                axis_number = re.search(r'#(.)', file).group(1)
                channel_name = f'_A{axis_number}'
            else:
                axis_number = ''
                channel_name = ''
            if '.dat' in file:
                with open(file, 'r') as dat_file:
                    config = [line.strip() for line in dat_file.readlines()]
                    trace_names = []
                    found_sampling_period = False
                    for line in config:
                        if '200,' in line:
                            trace_name_DE = line.split(',')[1]
                            match trace_name_DE:
                                case "Sollposition":
                                    trace_names.append("Position_Command")
                                case "Istposition":
                                    trace_names.append("Position")
                                case 'Positionsschleppfehler':
                                    trace_names.append('Position_Error')
                                case 'Geschwindigkeitsdifferenz':
                                    trace_names.append('Velocity_Error')
                                case "Motortemperatur":
                                    trace_names.append("Temperature")
                                case 'Istmoment':
                                    trace_names.append('Torque')
                                case 'Iststrom':
                                    trace_names.append('Current')
                                case _:
                                    trace_names.append(trace_name_DE)
                        if '241,' in line:
                            if not found_sampling_period:
                                sampling_period = int(float(line.split(',')[1]) * 1000)
                                found_sampling_period = True

                    for name in trace_names:
                        if name != 'Zeit':
                            data[f'{name}{channel_name}'] = []
            if '.r64' in file:
                channels = list(data.keys())
                current_axis_channels = []
                for channel in channels:
                    if axis_number in channel:
                        current_axis_channels.append(channel)
                with open(file, 'rb') as real64_file:
                    all_samples = np.fromfile(real64_file, dtype='float64')
                    # number_of_samples = int(len(all_samples) / len(current_axis_channels))
                    channel_number = 0
                    for sample in all_samples:

                        data[current_axis_channels[channel_number]].append(sample)
                        if channel_number < len(current_axis_channels) - 1:
                            channel_number += 1
                        else:
                            channel_number = 0
        for channel in data.keys():  #sekce bulharskych konstant
            if 'Motortemperatur' in channel:
                data[channel] = [sample - 273.15 for sample in data[channel]]
            if 'Position' in channel:
                data[channel] = [sample / 1000000 for sample in data[channel]]
            if 'Velocity' in channel:
                data[channel] = [sample / 6 for sample in data[channel]]  #neptej se... proste to tak je
        data['Sample'] = [x * sampling_period for x in range(len(data[channels[0]]))]
        return data
