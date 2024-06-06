# Data collector

This tool is made to collect sensor data from KUKA KR 3 R540 robotic arm. 
It collects the system vairables via a custom KRL submodule and trace data from
the KUKA Trace module.

![Robot Image](./images/KUKA.jpg)

For each of the 6 motors, the following variables are measured by system variables:
- Position
- Torque
- Current draw
- Temperature

This collects the data in real time with system variables. The main latency factor is
the network quality, so an ethernet connection is preffered over Wi-Fi. The data
is buffered on the robot side but has a hard-coded limit of 20000 samples. 
The sampling rate has to be configured in accordance of the length of an 
acquisition and with the network connection quality.

Besides the system variables, the robot controler can measure the traces of the robot.
It is a way intended by KUKA to recover data from the robot, that can measure the folowwing variables :
- Position : Command, measured, error
- Velocity error
- Torque
- Temperature
- Current

At the end of a measure sequence, tha traces are recovered from the network and saved in local to bea accessible.
KUKA Traces data is in binary format (.r64), with .dat, .trc and .txt associated.
Each motor has it's own file in that format, python will convert all the files and concatenate them to
return a readable file, as excel or csv. Note that you have to setup the network access to the robot
controler before launching this program to be able to recover the traces.

The data is acquired from a full-range motion of a motor. Each motor moves 
independently from each other.

The data collected by the program can be found in the /data folder, 
each data file having an explicit name with the date of the collection 
and details on the configuration.

**Example** : 
`[2024-05-17] 10h57 data [20%-60%] [36ms] [class 0] [10 10 10 10 10 10] - Robot 2`

**Format** : 
`[date] hour data [speed] [sampling rate] [load class] [number of iteration by axis] - N° of the robot`

**NB** : _The file obtained using KUKA Trace has a `_TRACE` suffix_

Summary
---
- [Measure Sequence](#measure-sequence)
- [UI Description and details](#ui-description-and-details)
    - [Collection settings](#collection-settings)
    - [KUKA traces](#kuka-traces)
    - [Robots loads](#robots-loads)
    - [Latency test](#latency-test)
    - [Gripper commands](#gripper-commands)
    - [Collected data plot](#collected-data-plot)
- [Program Structure](#program-structure)
- [KRL Submodule](#krl-submodule)
    - [Global variables](#global-variables)
    - `Data_collector.sub`
    - [KUKA Trace Configuration](#kuka-trace-configuration)
    - The `Axis_Main.src` program

## Measure Sequence

One measure run consists of a repetition of axis movement at a given speed. The numer of iterations by axis is variable and is defined by the user before launching the sequence. The speed of the robot can be modified to test the robot movement in diferent stress conditions.\
As data is recovered in time, this data collector has
a sampling rate. For the system variables, it varies from 12 to 60 milliseconds by a step of 12, the minimum
of time the KRL program can measure from internal timers.
KUKA traces provide a sampling rate from 1, 4 and 12ms, but oly the two last ones are implemented in this code.
Traces time sampling is more reliable than global variables.

## UI Description and details

As shown on the image below, the User Interface is divided in main 6 functions.

![GUI Screenshot](./images/GUI.png)

The PysimpleGUI librairy used in this application provide easy access to basic components of a gui, called widjets. For example, we can use buttons, keyboard input, checkboxes and combos. Combos are a way to give the user a visual choice on a variable. Note that all PysimpleGUI widjets give the possibility to run an action when an event occurs from it. Events are treated in the main loop of the program, and are defined as text by the programmer for each widjet. 

### Collection settings

This section defines the configuration for the data acquisition.

The following parameters can be configured:
- Number of movement iteration per axis
- Sampling rate
- Speed range for the test
   
Due to software limitations from the KRL environment, the sampling rate is
bound to be a multiple of 12. 

The speed of the motors during the acquisition varies according to the confifuration.
This value is defined as a percentage of the max value (i.e. 0 to 100). 
By default, the 'Constant' checkbox is set to true. It means that the robot speed will be constant for the whole test and thus only one acquisition is made. By clicking on the checkbox, it allows the user to set a range of speeds for the test, from minimum to maximum by a step.\
A test at multiple speed is equivalent to the merge of multiple single speed runs. So, check the configurations before launching an acquisition, even if it is able to stop between the runs if a problem has occurred. \
During a run at multple speed, system variables and KUKA traces are runing. To minimize data loss, we wait for each collection method to finish its process to start the next run.

### KUKA traces

A combo selector is used to select the KUKA Trace configuration that will be 
run along side of the system variable collection. The collected data is the same
as with the system variables but with more precision and reliability. 
The acquisition is done by the RTOS of the robot.

### Robots loads

Enter here the load on each robot, with weight or bungee coords
It will be displayed in the result dataset for data processing

### Latency test

Launch a latency test on the connected robots to print network timings
Plots a graph of the latency versus time and distributions with histograms

### Gripper commands

Command the gripper of the selected robot : open or close

### Collected data plot

Accessible without robot connection, this section plots data by selecting 
a excel file and hitting corresponding buttons

## Program Structure

The code is organized in two main parts in two folders : 
[`kuka`](./kuka) and [`ui`](./ui)

The `kuka` folder contains the classes to communicate with the robot controller 
and its varaiables. [`KUKA_Handler`](./kuka/handler.py), 
herited from [`openshowvar`](./kuka/kukavarproxy.py), 
is responsible of the connection to the robot controler. 
[`KUKA_Reader`](./kuka/reader.py) contains all the functions to operate a data 
collection, as buffer readings and formating the result into a 
[Pandas `DataFrame`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html).

The [`ui`](./ui) folder contains all the classes related to the user interface 
of the application. Python files with `ui_` prefixes generate the frames shown 
in the main window. The main window is generated by the 
[`MainWindow`](./ui/mainwindow.py) class, and latency measurement and robot 
measurement are in [`Measure_latency`](./ui/measure_latency.py) and 
[`Measure_robot`](./ui/measure_robot.py). 
The [`Measure_robot`](./ui/measure_robot.py) class contains the functions to 
execute a data collection, 
with the dynamic UI in [`CollectionGraphWindow`](./ui/graph_window.py) 
showing the robot data buffer state.

The [`main`](main.py) python file contains the main loop at the basis of the UI. 
It is done by a main class, and allows organization with class variables and 
class methods instead of global variables and functions.

## KRL Submodule

This section describes how to deploy the data collection on a cell.

### Global variables

The following declarations must be added in the `System/$config.dat` file 
on the robot KUKA workspace :

```
;FOLD ------DIAGNOSTIKA GLOBAL PROMENNE-------
;Program control
DECL BOOL PyRUN=FALSE
DECL BOOL PyDONE=FALSE
DECL INT PySPEED=30
DECL INT PyITER[6]
DECL BOOL PyOPEN_GRIPPER=FALSE
DECL BOOL PyCLOSE_GRIPPER=FALSE
DECL INT PyKNUCKLE
DECL REAL SPEED

;Data collection control
DECL BOOL ColRUN=FALSE
DECL BOOL ColRESET=FALSE
DECL BOOL ColBUFFER_FULL=FALSE
DECL BOOL ColKEEPING_UP=FALSE
DECL BOOL ColRESET_DONE=TRUE
DECL INT ColSAMPLING=12
DECL INT ColBUFFER_SIZE=20000

;Data communication buffers and flags
DECL INT SAMPLE_READ=772
DECL INT SAMPLE_NUMBER=772
DECL REAL __TAB_1[36]

DECL INT __PYTHON_HAS_READ=771 ; 
DECL BOOL __PyResetTimer=FALSE ; 

;Data collection buffers
DECL REAL ColBUFFER_TQ_A1[20000]
DECL REAL ColBUFFER_TQ_A2[20000]
DECL REAL ColBUFFER_TQ_A3[20000]
DECL REAL ColBUFFER_TQ_A4[20000]
DECL REAL ColBUFFER_TQ_A5[20000]
DECL REAL ColBUFFER_TQ_A6[20000]
DECL REAL ColBUFFER_TEMP_A1[20000]
DECL REAL ColBUFFER_TEMP_A2[20000]
DECL REAL ColBUFFER_TEMP_A3[20000]
DECL REAL ColBUFFER_TEMP_A4[20000]
DECL REAL ColBUFFER_TEMP_A5[20000]
DECL REAL ColBUFFER_TEMP_A6[20000]
DECL REAL ColBUFFER_CURR_A1[20000]
DECL REAL ColBUFFER_CURR_A2[20000]
DECL REAL ColBUFFER_CURR_A3[20000]
DECL REAL ColBUFFER_CURR_A4[20000]
DECL REAL ColBUFFER_CURR_A5[20000]
DECL REAL ColBUFFER_CURR_A6[20000]
DECL REAL ColBUFFER_TIME[20000]
DECL REAL ColBUFFER_ANALOG[20000]

DECL E6AXIS __LAST_POS_ACT
DECL E6AXIS ColBUFFER_POS_ACT[20000]
DECL E6AXIS __LAST_POS_MEAS
DECL E6AXIS ColBUFFER_POS_MEAS[20000]
;ENDFOLD
```

### `Data_collector.sub`

To allow for data collection, please be sure to add the `Data_collector.sub`
to the list of running submodules. This submodules takes up to **3 minutes** to 
properly initialize the internal data buffers.

This progam can be found in [`robot/KRL/`](./robot/KRL).

### KUKA Trace Configuration

Copy the provided configuration files found in [`robot/configurations/`](./robot/configurations) to
the `TRACE` folder of the robot.

**Example path** : `\\192.168.1.151\roboter\TRACE\`

### The `Axis_Main.src` program

The data collection uses the `Axis_Main.src` program to create the data 
to collect. It must be running in `AUT` mode at `100%` of run speed to produce
valid data.

This progam can be found in [`robot/KRL/`](./robot/KRL)`.