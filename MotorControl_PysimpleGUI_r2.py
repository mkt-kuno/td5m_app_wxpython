import PySimpleGUI as sg
import serial
import json
import csv
import tds530
import os
import argparse
#from icecream import ic

## How to make execute file 
# 1. run "/home/kuwano/Desktop/MotorControl/MotorControl_PysimpleGUI_r2.py"
#   then executable file will be in dist folder
# 2. edit "~~~~~~.desktop" file, ex) "MotorControl_PysimpleGUI_r2.desktop" in desktop
#   fix "Exec=" path to valid path
# 3. Double click to run

sg.theme('Black')

ARDUINO_BAUD_RATE = 115200
TDS530_BAUDRATE = 38400
TDS530_TIMEOUT_MS = 100/1000
ser = None
logger = None
parser = argparse.ArgumentParser()

parser.add_argument("--sport", help="Motor Control Port(Arduino Mega 2560)")
parser.add_argument("--lport", help="TDS530 Serial Port(TokyoSokki TDS530)")
args = parser.parse_args()

if args.sport:
    ser = serial.Serial(args.sport, ARDUINO_BAUD_RATE)
if args.lport:
    logger = tds530.TDS530(args.lport, TDS530_BAUDRATE, TDS530_TIMEOUT_MS)

## Win
if os.name == 'nt':
    if ser is None:
        ser = serial.Serial('COM3', ARDUINO_BAUD_RATE)
    if logger is None:
        logger = tds530.TDS530('COM4', TDS530_BAUDRATE, TDS530_TIMEOUT_MS)
## Linux
else:
    if ser is None:
        #ser = serial.Serial('/dev/ttyUSB0', ARDUINO_BAUD_RATE)
        ser = serial.Serial('/dev/ttyACM0', ARDUINO_BAUD_RATE)
    if logger is None:
        logger = tds530.TDS530('/dev/ttyUSB0', TDS530_BAUDRATE, TDS530_TIMEOUT_MS)

#フレーム定義
#ラベル表示フレーム
frame_Label = sg.Frame('',
        [
            [sg.Button('I',size=(20,50)),
             sg.Button('J',size=(20,50)), 
             sg.Button('K',size=(20,50)), 
             sg.Button('L',size=(20,50)), 
             sg.Button('M',size=(20,50))]
        ]
        , size = (1000, 50))

#変位表示フレーム
frame_Disp = sg.Frame('', 
        [
            
            [sg.Text('ローカル変位')],
            [
             sg.MLine(size=(20,100), key='-ML_I-'),
             sg.MLine(size=(20,100), key='-ML_J-'),
             sg.MLine(size=(20,100), key='-ML_K-'),
             sg.MLine(size=(20,100), key='-ML_L-'),
             sg.MLine(size=(20,100), key='-ML_M-')
            ]
        ], size = (1000, 100))

#移動用フレーム
frame_Move = sg.Frame('', 
        [
            [sg.Input(size=(20,100), key='-Input_I-'),
             sg.Input(size=(20,100), key='-Input_J-'),
             sg.Input(size=(20,100), key='-Input_K-'),
             sg.Input(size=(20,100), key='-Input_L-'),
             sg.Input(size=(20,100), key='-Input_M-'),
            ],
            [sg.Text('降下/上昇量(mm)を入力')]
        ], size = (1000, 100))

#ボタン用フレーム
frame_Button1 = sg.Frame('', 
        [
            [sg.Button('Slow\n2mm/min', key='-Slow-', size=(20,100), disabled=False),
             sg.Button('Fast\n10mm/min', key='-Fast-', size=(20,100), disabled=False),
             sg.Button('Set\nローカル座標を0に',  key='-Set-',  size=(20,100), disabled=False),
             sg.Button('Save',  key='-Save-',  size=(20,100), disabled=False),
             sg.Button('Save Stop',  key='-Savestop-',  size=(20,100), disabled=False)
            ]
        ], size = (1000, 100))

frame_Button2 = sg.Frame('', 
        [
             [sg.Button('Read\nファイル読み込み', key='-Read-', size=(20,100), disabled=False),
             sg.Button('Run',  key='-Run-',  size=(20,100), disabled=False),
             sg.Button('Stop', key='-Stop-', size=(20,100), disabled=False)
            ]
        ], size = (1000, 100))

#Preview用フレーム
frame_Preview = sg.Frame('', 
        [
            [sg.Text('Preview'),sg.MLine(size=(500,100), key='-ML_Preview-')],
        ], size = (1000, 200))

#Status用フレーム
frame_Status = sg.Frame('', 
        [
            [sg.Text('Status'), sg.MLine(size=(100,100), key='-ML_Status-')],
        ], size = (1000, 100))

layout = [
    [frame_Label],
    [frame_Disp],
    [frame_Move],
    [frame_Button1],
    [frame_Button2],
    [frame_Preview],
    [frame_Status]
]

window = sg.Window('MonitorControl', layout, resizable = True)

list_gcode = []
list_gcode_index = 0
is_running = False
is_saving = None
list_savefile = [['Time', 'Status', 'I', 'J', 'K', 'L', 'M']]
csv_header = ['Time', 'Status', 'I', 'J', 'K', 'L', 'M', 
              'Time', '000', '001', '002', '003', '004', '005', '006', '007', '008', '009', 
                '010', '011', '012', '013', '014', '015', '016', '017', '018', '019', 
                '020', '021', '022', '023', '024', '025', '026', '027', '028', '029', 
                '030', '031', '032', '033', '034', '035', '036', '037', '038', '039', 
                '040', '041', '042', '043', '044', '045', '046', '047', '048', '049']

logger.start()

while True:
    event, values = window.read(timeout=10)
    
    ############################### Datalogger ###############################
    log = logger.read()
    if log is not None:
        #print(type(log['000']))
        print(log)

    ############################### EVENT ###############################
    # Read
    if event == '-Read-':
        # gcodeのファイル指定すること
        gcode = './MotorControl.txt'
        with open(gcode) as g:
            g_preview = g.read()
            window['-ML_Preview-'].update(g_preview)
        with open(gcode) as g:
            list_gcode = g.readlines()
            list_gcode_index = 0

    #Run  
    if event ==  '-Run-':
        is_running = True
    #インクリメント指令（Slow）
    if event == '-Slow-':
            g_slow =  'G91' + 'I' + values['-Input_I-'] + 'J' + values['-Input_J-'] + 'K' + values['-Input_K-'] + 'L' + values['-Input_L-'] + 'M' + values['-Input_M-'] + 'V2 W2 X2 Y2 Z2 \r\n'
            print(g_slow)
            ser.write(g_slow.encode('ascii'))
            ser.flush()
            window['-ML_Preview-'].update(g_slow)
    #インクリメント指令（Fast）   
    if event == '-Fast-':
            g_fast =   'G91' + 'I' + values['-Input_I-'] + 'J' + values['-Input_J-'] + 'K' + values['-Input_K-'] + 'L' + values['-Input_L-'] + 'M' + values['-Input_M-'] + 'V10 W10 X10 Y10 Z10 \r\n'
            ser.write(g_fast.encode('ascii'))
            ser.flush()
            window['-ML_Preview-'].update(g_fast)
    #ローカル座標設定
    if event == '-Set-':
            # g_set =  'G52' + 'I' + values['-Input_I-'] + 'J' + values['-Input_J-'] + 'K' + values['-Input_K-'] + 'L' + values['-Input_L-'] + 'M' + values['-Input_M-'] + '\r\n'
            g_set =  'G52 I0J0K0L0M0\r\n'
            ser.write(g_set.encode('ascii'))
            ser.flush()
            window['-ML_Preview-'].update(g_set)
    
    #SaveFile
    if event == '-Save-':
        is_saving = True
        with open('./Time&Disp.csv', 'a', newline="") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(csv_header)
             
    if event == '-Savestop-':
        is_saving = False
             
             
            
    #ローカル座標設定
    if event == '-Set-':
        # g_set =  'G52' + 'I' + values['-Input_I-'] + 'J' + values['-Input_J-'] + 'K' + values['-Input_K-'] + 'L' + values['-Input_L-'] + 'M' + values['-Input_M-'] + '\r\n'
        g_set =  'G52 I0J0K0L0M0\r\n'
        ser.write(g_set.encode('ascii'))
        ser.flush()
        window['-ML_Preview-'].update(g_set)
           
    if event is None:
            print('exit')
            break
    
    ############################### GCODE ###############################
    ser_line = ""
    ser_json = None
    try:
        ser_line = ser.readline().decode('ascii')
        if "REPORT: " in ser_line:
            ser_json = json.loads(ser_line.replace("REPORT: ", ''))
    except:
        pass
    
    if ser_json is None:
        continue
    
    print(ser_json)
    #print(type(ser_json['Time']))
    window['-ML_I-'].update(ser_json['I'])
    window['-ML_J-'].update(ser_json['J'])
    window['-ML_K-'].update(ser_json['K'])
    window['-ML_L-'].update(ser_json['L'])
    window['-ML_M-'].update(ser_json['M'])
    window['-ML_Status-'].update(ser_json['Status'])

    #　Status：BUSY　でボタン無効化
    if ser_json['Status'] == 'BUSY':
        window['-Slow-'].update(disabled=True)
        window['-Fast-'].update(disabled=True)
        window['-Set-'].update(disabled=True)
        window['-Run-'].update(disabled=True)
        window['-Read-'].update(disabled=True)
        #window['-Stop-'].update(disabled=True)
        
    if ser_json['Status'] == 'IDLE' and is_running == False:
        window['-Slow-'].update(disabled=False)
        window['-Fast-'].update(disabled=False)
        window['-Set-'].update(disabled=False)
        window['-Run-'].update(disabled=False)
        window['-Read-'].update(disabled=False)
        #window['-Stop-'].update(disabled=False)

    if is_running:
        if ser_json['Status'] == 'IDLE':
            if list_gcode_index >= 0 and list_gcode_index < len(list_gcode):
            
                gc = list_gcode[list_gcode_index]
                print(gc)
                ser.write(gc.encode('ascii') + '\r\n'.encode('ascii')) 
                ser.flush()
                window['-ML_Preview-'].update(gc)
                list_gcode_index += 1
            else:
                window['-ML_Preview-'].update("Finish!!")
                list_gcode_index = -1
                list_gcode = []
                is_running = False
        if ser_json['Status'] == 'BUSY':
            pass                

    if is_saving is True:
        window['-Save-'].update(disabled=True)
        with open('./Time&Disp.csv', 'a', newline="") as f:
            writer = csv.writer(f, delimiter=",")
        # Time,Displacement
           #writer.writerow([ser_json['Time'], ser_json['Status'], ser_json['I'], ser_json['J'], ser_json['K'], ser_json['L'], ser_json['M']])
            
            if log is not None:
                writer.writerow([ser_json['Time'], ser_json['Status'], ser_json['I'], ser_json['J'], ser_json['K'], ser_json['L'], ser_json['M'], 
                                log['Time'], log['000'], log['001'], log['002'], log['003'], log['004'], log['005'], log['006'], log['007'], log['008'], log['009'], 
                                log['010'], log['011'], log['012'], log['013'], log['014'], log['015'], log['016'], log['017'], log['018'], log['019'], 
                                log['020'], log['021'], log['022'], log['023'], log['024'], log['025'], log['026'], log['027'], log['028'], log['029'], 
                                log['030'], log['031'], log['032'], log['033'], log['034'], log['035'], log['036'], log['037'], log['038'], log['039'], 
                                log['040'], log['041'], log['042'], log['043'], log['044'], log['045'], log['046'], log['047'], log['048'], log['049']])

    if is_saving is False:
        window['-Save-'].update(disabled=False)
        is_saving = None
        
window.close()


   
   

