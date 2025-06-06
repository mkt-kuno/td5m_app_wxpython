import wx
import wxasync
import asyncio
import serial
import aioserial
import time
import copy
import argparse
import tds

ARDUINO_BAUD_RATE = 115200
TDS530_BAUDRATE = 38400
TDS530_TIMEOUT_MS = 100/1000

parser = argparse.ArgumentParser()
parser.add_argument("--sport", help="Motor Control Port(Arduino Mega 2560)")
parser.add_argument("--lport", help="TDS530 Serial Port(TokyoSokki TDS530)")
args = parser.parse_args()

class MainFrame(wx.Frame):
    def __init__(self, parent=None):
        super(MainFrame, self).__init__(parent, style=wx.DEFAULT_FRAME_STYLE^wx.RESIZE_BORDER^wx.MAXIMIZE_BOX)
        
        self.SetTitle("5TD Motor Controller and Monitor (wxPython)")
        self.SetSize((800, 1000))
        self.SetMinSize((800, 1000))
        self.SetMaxSize((800, 1000))

        self.SetFont(wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Consolas'))
        _small_font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Consolas')

        self.item_dict = {}
        self.item_dict['I'] = {}
        self.item_dict['J'] = {}
        self.item_dict['K'] = {}
        self.item_dict['L'] = {}
        self.item_dict['M'] = {}
        self.item_dict["param"] = {}
        self.item_dict['button'] = {}

        v_box = wx.BoxSizer(wx.VERTICAL)

        displacement_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Local (Current) Position[mm]")
        if (displacement_box):
            g_sizer = wx.GridSizer(rows=2, cols=5, gap=(5, 5))

            g_sizer.Add(wx.StaticText(self, label="I [o____]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
            g_sizer.Add(wx.StaticText(self, label="J [_o___]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
            g_sizer.Add(wx.StaticText(self, label="K [__o__]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
            g_sizer.Add(wx.StaticText(self, label="L [___o_]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
            g_sizer.Add(wx.StaticText(self, label="M [____o]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)

            _label_def = "0.000"
            self.item_dict["I"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE|wx.BORDER_SIMPLE)
            self.item_dict["J"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE|wx.BORDER_SIMPLE)
            self.item_dict["K"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE|wx.BORDER_SIMPLE)
            self.item_dict["L"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE|wx.BORDER_SIMPLE)
            self.item_dict["M"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE|wx.BORDER_SIMPLE)

            g_sizer.Add(self.item_dict["I"]["displacement"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["J"]["displacement"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["K"]["displacement"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["L"]["displacement"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["M"]["displacement"], 1, wx.EXPAND)

            displacement_box.Add(g_sizer, 0, wx.EXPAND|wx.ALL, 5)
        v_box.Add(displacement_box, 0, wx.EXPAND|wx.ALL, 5)

        incremental_box = wx.StaticBoxSizer(wx.VERTICAL, self, "[G91] Increment Move[mm] (+:Ascending, -:Descending)")
        if (incremental_box):
            g_sizer = wx.GridSizer(rows=2, cols=5, gap=(5, 5))

            g_sizer.Add(wx.StaticText(self, label="I [o____]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
            g_sizer.Add(wx.StaticText(self, label="J [_o___]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
            g_sizer.Add(wx.StaticText(self, label="K [__o__]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
            g_sizer.Add(wx.StaticText(self, label="L [___o_]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
            g_sizer.Add(wx.StaticText(self, label="M [____o]", style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE), 1, wx.EXPAND)
        
            self.item_dict["I"]["input"]    = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
            self.item_dict["J"]["input"]    = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
            self.item_dict["K"]["input"]    = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
            self.item_dict["L"]["input"]    = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
            self.item_dict["M"]["input"]    = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)

            g_sizer.Add(self.item_dict["I"]["input"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["J"]["input"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["K"]["input"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["L"]["input"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["M"]["input"], 1, wx.EXPAND)

            incremental_box.Add(g_sizer, 0, wx.EXPAND|wx.ALL, 5)
        v_box.Add(incremental_box, 0, wx.EXPAND|wx.ALL, 2)

        command_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Commands")
        if (command_box):
            g_sizer = wx.GridSizer(rows=3, cols=3, gap=(5, 5))

            self.item_dict["button"]["g91_slow"] = wx.Button(self, label="[G91]Increment Move\nSlow 2mm/min", style=wx.BU_EXACTFIT)
            self.item_dict["button"]["g91_fast"] = wx.Button(self, label="[G91]Increment Move\nFast 10mm/min", style=wx.BU_EXACTFIT)
            self.item_dict["button"]["g52_set"] = wx.Button(self, label="[G52]Set Local Pos\n IJKLM all Zero", style=wx.BU_EXACTFIT)

            self.item_dict["button"]["gcode_load"] = wx.Button(self, label="GCode\nLoad from File", style=wx.BU_EXACTFIT)
            self.item_dict["button"]["gcode_start"] = wx.Button(self, label="GCode\nStart Control", style=wx.BU_EXACTFIT)
            self.item_dict["button"]["gcode_stop"] = wx.Button(self, label="GCode\nStop Control", style=wx.BU_EXACTFIT)

            self.item_dict["button"]["save_start"] = wx.Button(self, label="File Saving\nStart", style=wx.BU_EXACTFIT)
            self.item_dict["button"]["save_stop"] = wx.Button(self, label="File Saving\nStop", style=wx.BU_EXACTFIT)

            # disable stop button at start
            self.item_dict["button"]["save_stop"].Enable(False)
            self.item_dict["button"]["gcode_stop"].Enable(False)

            g_sizer.Add(self.item_dict["button"]["g91_slow"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["button"]["g91_fast"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["button"]["g52_set"], 1, wx.EXPAND)

            g_sizer.Add(self.item_dict["button"]["gcode_load"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["button"]["gcode_start"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["button"]["gcode_stop"], 1, wx.EXPAND)

            g_sizer.Add(self.item_dict["button"]["save_start"], 1, wx.EXPAND)
            g_sizer.Add(self.item_dict["button"]["save_stop"], 1, wx.EXPAND)

            command_box.Add(g_sizer, 0, wx.EXPAND|wx.ALL, 5)
        v_box.Add(command_box, 0, wx.EXPAND|wx.ALL, 5)

        # Scrollable area for Gcode preview, and readonly text control
        gcode_box = wx.StaticBoxSizer(wx.VERTICAL, self, "GCode Preview")
        if (gcode_box):
            self.item_dict["gcode"] = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_PROCESS_ENTER)
            # small font for gcode text
            self.item_dict["gcode"].SetFont(wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, 'Consolas'))
            gcode_box.Add(self.item_dict["gcode"], 1, wx.EXPAND|wx.ALL, 5)
        v_box.Add(gcode_box, 1, wx.EXPAND|wx.ALL, 5)
        
        # status box for many params
        status_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Params")
        if (status_box):
            NUM_DIV = 10
            g_sizer = wx.GridSizer(rows=12, cols=NUM_DIV, gap=(5, 5))

            for start_ch in range(0, 50, NUM_DIV):
                for ch in range(start_ch, start_ch+NUM_DIV):
                    _name = "%03d"%ch
                    _label = wx.StaticText(self, label=_name, style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
                    _label.SetFont(_small_font)
                    g_sizer.Add(_label, 1, wx.EXPAND)
                for ch in range(start_ch, start_ch+NUM_DIV):
                    _name = "TDS%03d"%ch
                    _status = wx.StaticText(self, label="0.000", style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE|wx.BORDER_SIMPLE)
                    _status.SetFont(_small_font)
                    g_sizer.Add(_status, 1, wx.EXPAND)
                    self.item_dict["param"][_name] = _status


            _labels = ["I[o____]", "J[_o___]", "K[__o__]", "L[___o_]", "M[____o]", "Time1", "Time2", "Status", "Control", "Save", ]
            for label in _labels:
                _label = wx.StaticText(self, label=label, style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
                _label.SetFont(_small_font)
                g_sizer.Add(_label, 1, wx.EXPAND)

            _statuss = ["I", "J", "K", "L", "M", "time1", "time2", "status", "control", "save"]
            for _status in _statuss:
                _item = wx.StaticText(self, label="0.000", style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE|wx.BORDER_SIMPLE)
                _item.SetFont(_small_font)
                g_sizer.Add(_item, 1, wx.EXPAND)
                if _status == "-----":
                    continue
                self.item_dict["param"][_status] = _item

            self.item_dict["param"]["status"].SetLabel("IDLE")
            self.item_dict["param"]["time1"].SetLabel("00/01/01")
            self.item_dict["param"]["time2"].SetLabel("00:00:00")
            self.item_dict["param"]["control"].SetLabel("False")
            self.item_dict["param"]["save"].SetLabel("False")

            status_box.Add(g_sizer, 0, wx.EXPAND|wx.ALL, 5)
        v_box.Add(status_box, 0, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(v_box)
        self.Layout()

        wxasync.AsyncBind(wx.EVT_BUTTON, self.button_g91_slow,      self.item_dict["button"]["g91_slow"])
        wxasync.AsyncBind(wx.EVT_BUTTON, self.button_g91_fase,      self.item_dict["button"]["g91_fast"])
        wxasync.AsyncBind(wx.EVT_BUTTON, self.button_g52_set,       self.item_dict["button"]["g52_set"])
        wxasync.AsyncBind(wx.EVT_BUTTON, self.button_gcode_load,    self.item_dict["button"]["gcode_load"])
        wxasync.AsyncBind(wx.EVT_BUTTON, self.button_gcode_start,   self.item_dict["button"]["gcode_start"])
        wxasync.AsyncBind(wx.EVT_BUTTON, self.button_gcode_stop,    self.item_dict["button"]["gcode_stop"])
        wxasync.AsyncBind(wx.EVT_BUTTON, self.button_save_start,    self.item_dict["button"]["save_start"])
        wxasync.AsyncBind(wx.EVT_BUTTON, self.button_save_stop,     self.item_dict["button"]["save_stop"])
        
        # self.ser_reader, ser_writer
        # self.ser_reader, self.ser_writer = await serial_asyncio.open_serial_connection(url=args.sport, baudrate=ARDUINO_BAUD_RATE)
        # global logger
        
        try:
            self._logger = tds.TDS530(port='/dev/ttyUSB0', baudrate=TDS530_BAUDRATE)
            self._logger.start()
        except Exception as e:
            pass

        self.is_saving:bool = False
        self.path_saving:str = ""
        self.task_saving = None

        self.is_controlling:bool = False
        self.task_controlling = None

        wxasync.StartCoroutine(self.logger_loop, self)
        wxasync.StartCoroutine(self.ser_arduino_loop, self)
    
    async def file_save_loop(self):
        while self.is_saving:
            if self.path_saving != "":
                print("Saving data to file to %s..." % self.path_saving)
                # Save data to file
                # This is a placeholder for actual saving logic
                pass
            await asyncio.sleep(0.5)

    async def gcode_process_loop(self):
        while self.is_controlling:
            # Process GCode commands
            # This is a placeholder for actual GCode processing logic
            await asyncio.sleep(0.5)

    async def logger_loop(self):
        while True:
            await asyncio.sleep(0.2)
            _ret:dict = await self._logger.read()

            if not "time" in _ret:
                continue
            
            _dt = _ret["time"]
            self.item_dict["param"]["time1"].SetLabel(_dt.strftime('%Y/%m/%d')[2:])
            self.item_dict["param"]["time2"].SetLabel(_dt.strftime('%H:%M:%S'))

            for ch in range(50):
                _val = "%.1f" % _ret["%03d"%ch]
                self.item_dict["param"]["TDS%03d"%ch].SetLabel(_val)

    async def ser_arduino_loop(self):
        while True:
            ## ser(Arduino) と通信し続ける
            
            await asyncio.sleep(1)

    async def button_g91_slow(self, event):
        # Gcode を生成してバッファリングするだけ
        pass

    async def button_g91_fase(self, event):
        # Gcode を生成してバッファリングするだけ
        pass

    async def button_g52_set(self, event):
        # Gcode を生成してバッファリングするだけ
        pass

    async def button_gcode_load(self, event):
        # Gcode を読込してバッファリングするだけ
        pass

    async def button_gcode_start(self, event):
        # Check if GCode is loaded
        ## @todo GCodeバッファが空であればReturn

        # Enable stop button
        self.item_dict["button"]["gcode_stop"].Enable(True)
        # Disable start button
        self.item_dict["button"]["gcode_start"].Enable(False)
        # disable Load button
        self.item_dict["button"]["gcode_load"].Enable(False)
        self.item_dict["button"]["g91_slow"].Enable(False)
        self.item_dict["button"]["g91_fast"].Enable(False)
        self.item_dict["button"]["g52_set"].Enable(False)

        # Start GCode processing
        self.is_controlling = True
        self.task_controlling = wxasync.StartCoroutine(self.gcode_process_loop, self)

    async def button_gcode_stop(self, event):
        # Disable stop button
        self.item_dict["button"]["gcode_stop"].Enable(False)
        # Stop GCode processing
        self.is_controlling = False
        if self.task_controlling is not None:
            self.task_controlling.cancel()
            self.task_controlling = None
        
        ## @todo 実際にはGcodeのバッファをクリアして、StatusがIDLEになるまで待つ

        # Enable start button
        self.item_dict["button"]["gcode_start"].Enable(True)
        # Enable Load button
        self.item_dict["button"]["gcode_load"].Enable(True)
        self.item_dict["button"]["g91_slow"].Enable(True)
        self.item_dict["button"]["g91_fast"].Enable(True)
        self.item_dict["button"]["g52_set"].Enable(True)
        pass

    async def button_save_start(self, event):
        # Start saving data
        dlg = wx.FileDialog(self, 
                            message="Save data to file", 
                            wildcard="CSV files (*.csv)|*.csv", 
                            defaultDir=wx.StandardPaths.Get().GetDocumentsDir(), 
                            defaultFile=time.strftime('wx5td_%Y%m%d%H%M%S.csv'),
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        response  = await wxasync.AsyncShowDialogModal(dlg)
        if response== wx.ID_CANCEL:
            # User cancelled the dialog
            return
        # Get the path to the file
        self.path_saving = dlg.GetPath()
        if not self.path_saving:
            return
        # Here you would start the saving process, e.g., open a file and write data
        print(f"Saving data to {self.path_saving}...")
        
        # Enable stop button
        self.item_dict["button"]["save_stop"].Enable(True)
        # Disable start button
        self.item_dict["button"]["save_start"].Enable(False)
        self.is_saving = True
        # Start the file saving loop
        self.task_saving = wxasync.StartCoroutine(self.file_save_loop, self)

    async def button_save_stop(self, event):
        # Enable start button
        self.item_dict["button"]["save_start"].Enable(True)
        # Disable stop button
        self.item_dict["button"]["save_stop"].Enable(False)
        # Stop saving data
        self.is_saving = False
        self.path_saving = ""
        if self.task_saving is not None:
            self.task_saving.cancel()
            self.task_saving = None
        print("Saving stopped.")

async def main():
    app = wxasync.WxAsyncApp()
    frame = MainFrame()
    frame.Show()
    app.SetTopWindow(frame)
    await app.MainLoop()


asyncio.run(main())
