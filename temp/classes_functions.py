import numpy as np
import re
import pandas as pd
import PySimpleGUI as sg
import matplotlib.pyplot as plt
import os


#######################################################################################################################
#########################################    F U N C T I O N S   ######################################################
#######################################################################################################################

def plot_selector(data_file):
    layout = []
    layout.append([sg.Text('Select channels to plot:', font=(15))])
    for channel in data_file.keys():
        if channel != 'Sample':
            layout.append([sg.Checkbox(text=channel, key=str(channel), default=True)])
    layout.append([sg.Button('Select All', key='-BTN_ALL-'),
                   sg.Button('Deselect All', key='-BTN_NONE-')])
    layout.append([sg.Button('Ok', key='-Ok-'), sg.Exit()])
    window_s = sg.Window('Select Channels', layout, finalize=True)

    while True:
        event, values = window_s.read()

        if event == '-Ok-':
            output_data = {'Sample': data_file['Sample']}
            for channel in data_file.keys():
                if ('_' or 'time') in channel:
                    # if not ('filename' in channel or 'Sample' in channel):
                    if values[channel]:
                        output_data[channel] = data_file[channel]

            window_s.Close()
            return output_data

        if event == '-BTN_ALL-':
            for channel in data_file.keys():
                if channel != 'Sample':
                    window_s[channel].update(True)

        if event == '-BTN_NONE-':
            for channel in data_file.keys():
                if channel != 'Sample':
                    window_s[channel].update(False)

        if event == sg.WIN_CLOSED or event == 'Exit':
            break

def item_counter(list):
    value_count = 0
    output = []
    for index in range(1, len(list)):
        new_value = list[index]
        last_value = list[index - 1]
        if new_value == last_value:
            value_count += 1
        else:
            value_count += 1
            output.append(value_count)
            value_count = 0
    count_dict = {}
    for item in output:
        if item in count_dict:
            count_dict[item] += 1
        else:
            count_dict[item] = 1
    for key, value in count_dict.items():
        print(f"Prvek {key} se vyskytuje {value}x.")
    print('******************************************')

def create_figure(data_dict):
    plt.rcParams.update({'font.size': 11})
    plt.figure(figsize=(10, 4))
    color_pallet = ['b', 'r', 'g', 'k', 'c', 'm', 'y']
    plot_color = 0
    if not isinstance(data_dict['Sample'][1], float):
        data_dict['Sample'] = [x / 1000 for x in data_dict['Sample']]
    for channel in data_dict:

        label = channel
        # label = channel.split('(')[0]
        # label = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6']
        # label = ['A1 setpoint position (°)', 'A1 actual position (°)']
        # label = ['No load','Bungee Cord 1' ,'Bungee Cord 1 + 2']
        # label = ['0 g','2000 g', '1000 g']

        # label = channel
        if channel != 'Sample':
            # if 'AXIS_ACT' in channel:
            #     if 'TORQUE' in channel:
            #         label = channel + ' (Nm)'
            #     else:
            #         label = channel + ' (°)'
            # if 'MOT_TEMP' in channel:
            #     label = channel + ' (°C)'
            # if 'CURR' in channel:
            #     label = channel + ' (%)'
            # if 'time' in channel:
            #     label = channel.split('(')[0] + ' (ms)'
            # item_counter(data_dict[channel])
            plt.plot(data_dict['Sample'], data_dict[channel], color=color_pallet[plot_color % len(color_pallet)],
                     label=label)  # label=label[plot_color]
            plot_color += 1
    # plt.suptitle('Values of the Selected Variables Over Time')
    # plt.xlabel('Time (ms)')
    plt.xlabel('Time (s)')
    plt.ylabel('Axis A5, Actual torque (Nm)')
    # plt.ylabel('Variable')
    plt.legend(loc='upper right', ncol=1)
    # plt.legend(bbox_to_anchor=(1, 1.2),loc='upper right',ncol = 3)
    plt.grid(True)
    plt.xlim([0, 15])
    directory = r'D:\VSB\Data collection app - THESIS\data'
    plt.savefig(directory + r'\graf.pdf', format="pdf", bbox_inches="tight")
    plt.show()

def import_data(files):
    dictionaries = []
    layout = []
    for index in range(len(files)):
        dataset = {}
        dictionaries.append(dataset)
    for file, index in zip(files, range(len(files))):
        df = pd.read_csv(file, sep=';')
        for channel in df.columns:
            dictionaries[index][channel] = df[channel].tolist()
        dictionaries[index]['Filename'] = file.split('/')[-1]

    trace_channels = [[] for _ in dictionaries]
    for dataset, index in zip(dictionaries, range(len(dictionaries))):
        for channel in dataset.keys():
            if not ('Filename' in channel or 'Sample' in channel):
                trace_channels[index].append(channel)

    tabs = [[] for _ in dictionaries]
    tab_groups = []
    for index in range(len(dictionaries)):
        tabs[index].append([sg.Text('Number of samples: ' + str(len(dictionaries[index]['Sample'])))])
        tabs[index].append([sg.Text('Sampling period: ' + str(dictionaries[index]['Sample'][1]) + ' ms')])
        for channel in dictionaries[index].keys():
            if not ('Filename' in channel or 'Sample' in channel):
                tabs[index].append([sg.Checkbox(text=channel, key=str(channel + str(index)))])

    layout.append([sg.Text('Select channels to plot:', font=(15))])
    for dataset, index in zip(dictionaries, range(len(dictionaries))):
        tab_groups.append(sg.Tab(dataset['Filename'], tabs[index]))
    layout.append([sg.TabGroup([tab_groups])])
    layout.append([sg.Button('Ok', key='-Ok-'), ])
    window_s = sg.Window('Select Channels', layout, finalize=True, grab_anywhere=True)

    same_sampling = [dictionaries[index]['Sample'][1] == dictionaries[0]['Sample'][1] for index in
                     range(len(dictionaries))]  # Check, if all the datasets have the same sampling rate
    if not all(same_sampling):
        sg.Popup('Not all imported datasets have the same sampling rate.\n'
                 'Comparing such channels is irrelevant.', title='Warning', font=13)

    while True:
        event, values = window_s.read()

        if event == '-Ok-':

            sample_channel = []
            for index in range(len(dictionaries)):
                sample_channel.append(dictionaries[index]['Sample'])
            output_data = {'Sample': min(sample_channel, key=len)}
            shortest_channel_length = len(output_data['Sample'])
            for index in range(len(dictionaries)):
                for channel in dictionaries[index]:
                    if not ('Filename' in channel or 'Sample' in channel) and values[channel + str(index)]:
                        output_data[channel + ' (' + str(dictionaries[index]['Filename']) + ')'] = \
                            dictionaries[index][channel][0:shortest_channel_length]
            window_s.Close()
            return output_data

        if event == sg.WIN_CLOSED or event == 'Exit':
            window_s.Close()
            return None

def convert_trace_data(file_names):
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
                trace_units = []
                found_sampling_period = False
                for line in config:
                    if '200,' in line:
                        trace_names.append(line.split(',')[1])
                    if '202,' in line:
                        trace_units.append(line.split(',')[1])
                    if '241,' in line:
                        if not found_sampling_period:
                            sampling_period = int(float(line.split(',')[1]) * 1000)
                            found_sampling_period = True

                for name, unit in zip(trace_names, trace_units):
                    if name != 'Zeit':
                        data[f'{name}{channel_name} ({unit})'] = []
        if '.r64' in file:
            channels = list(data.keys())
            current_axis_channels = []
            for channel in channels:
                if axis_number in channel:
                    current_axis_channels.append(channel)
            with open(file, 'rb') as real64_file:
                all_samples = np.fromfile(real64_file, dtype='float64')
                number_of_samples = int(len(all_samples) / len(current_axis_channels))
                channel_number = 0
                for sample in all_samples:

                    data[current_axis_channels[channel_number]].append(sample)
                    if channel_number < len(current_axis_channels) - 1:
                        channel_number += 1
                    else:
                        channel_number = 0
    for channel in data.keys():
        if 'Motortemperatur' in channel:
            data[channel] = [sample - 273.15 for sample in data[channel]]
        if 'position' in channel:
            data[channel] = [sample / 1000000 for sample in data[channel]]
    data['Sample'] = [x * sampling_period for x in range(len(data[channels[0]]))]
    return data

def config_dialog():
    default_directory = r'D:\VSB\Data collection app - THESIS\data'
    sg.theme('GrayGrayGray')
    layout = [
        [sg.Text('Please insert IP address and Port number of the robot controller:')],
        [sg.Text('IP Address:', size=(10, 1)), sg.InputText(size=(15, 1), key='-IP-', default_text='192.168.1.152')],
        [sg.Text('Port Number:', size=(10, 1)), sg.InputText(size=(15, 1), key='-port-', default_text='7000')],
        [sg.T('')],
        [sg.Text('Choose working directory:')],
        [sg.Input(default_text=default_directory, key='-user_path-', size=(60, 1)),
         sg.FolderBrowse(initial_folder=default_directory, key='-browse-')],
        [sg.T('')], [sg.Text('Run Data Collection Application in:')],
        [sg.Button('Online mode', key='-Confirm_on-', button_color='#77DB00'),
         sg.Button('Offline mode', key='-Confirm_off-')]]
    window = sg.Window('Initial Setup', layout, keep_on_top=True, modal=True,
                       element_justification='c', icon='V2/V2.5/icon/setup_icon.ico')

    while True:
        event, values = window.read()
        config_errors = []
        if event == sg.WIN_CLOSED:
            quit()
        if 'Confirm' in event:
            try:
                if os.path.exists(values['-user_path-']):
                    directory = values['-user_path-']
                    trace_path = os.path.join(directory, "trace")
                    if not os.path.exists(trace_path):
                        os.makedirs(trace_path)
                    csv_path = os.path.join(directory, "csv")
                    if not os.path.exists(csv_path):
                        os.makedirs(csv_path)
                else:
                    directory = ''
                    config_errors.append('- Working directory does not exist\n')

                if 'off' in event:
                    offline_mode = True
                    if not bool(config_errors):
                        window.close()
                        return 0, 0, directory, offline_mode
                    else:
                        sg.popup_ok(''.join(config_errors), title='ERROR', font=14, modal=True,
                                    icon='V2/V2.5/icon/error_icon.ico', keep_on_top=True)
                else:
                    ip_address = values['-IP-']
                    parts = ip_address.split('.')
                    if len(parts) != 4:
                        config_errors.append('- Invalid IPv4 Address Format.\n')
                    else:
                        try:
                            for part in parts:
                                if not 0 <= int(part) <= 255:
                                    config_errors.append('- IP Address number out of range.\n')
                                    break
                        except ValueError:
                            config_errors.append('- IP address must contain integer values only.\n')
                    try:
                        port_number = int(values['-port-'])
                        if not 0 <= port_number <= 65535:
                            config_errors.append('- Port number out of range.')
                    except ValueError:
                        config_errors.append('- Port number must be an integer value.\n')
                    else:
                        offline_mode = False
                        if not bool(config_errors):
                            window.close()
                            return ip_address, port_number, directory, offline_mode
                        else:
                            sg.popup_ok(''.join(config_errors), title='ERROR', font=14, modal=True,
                                        icon='V2/V2.5/icon/error_icon.ico', keep_on_top=True)
            except Exception as e:
                sg.popup_ok(e)

def open_help():
    sg.theme('GrayGrayGray')
    help_path = r'D:\VSB\Data collection app - THESIS\data'
    with open(help_path, 'r', encoding='utf-8') as file:
        help_text = file.read()

    layout = [[sg.Multiline(default_text=help_text, size=(90, 40), disabled=True, font=('Consolas', 14))],
              [sg.Button('Close', )]]

    window_help = sg.Window('Help', layout, font=16, element_justification='c')
    while True:
        event, values = window_help.read()
        if event in (sg.WIN_CLOSED, 'Close'):
            window_help.close()
            break