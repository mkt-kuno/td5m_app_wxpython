import wx
from wxasync import AsyncBind, WxAsyncApp, StartCoroutine
import asyncio
import serial
import serial_asyncio
import time
import copy
import argparse

ARDUINO_BAUD_RATE = 115200
TDS530_BAUDRATE = 38400
TDS530_TIMEOUT_MS = 100/1000

logger = None
ser_reader, ser_writer = None, None

class TDS530:
    def __init__(self, port = '/dev/ttyUSB0', baudrate = 38400, timeout=0):
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._buffer = {}
        self._queue: asyncio.Queue[dict] = asyncio.Queue()

    def start(self, writer):
        self.reader.reset_input_buffer()
        self.writer.reset_output_buffer()
        self.writer.write('ST\r\n'.encode('ascii'))

    def _cmd_start(self, writer):
        self.reader.reset_input_buffer()
        self.writer.reset_output_buffer()
        self.writer.write('ST\r\n'.encode('ascii'))

    async def task(self):
        self.reader, self.writer = await serial_asyncio.open_serial_connection(
            protocol_factory=lambda: self,
            url=self._port,
            baudrate=self._baudrate
        )
        
        while (True):
            # if not self.reader.readable():
            #     await asyncio.sleep(0.01)
            #     continue
            line = await self.reader.readline()

            if line is None:
                continue
            line = line.decode('ascii').replace('\r\n', '')
            if line == '':
                continue
            if "ERR" in line:
                print("ERROR")
                # @todo もしエラーが出てしまうなら考慮する
            elif len(line) > 1 and line[0] == '2':
                # Time型表記
                #tm = time.strptime(line, '%Y/%d/%m %H:%M:%S')
                #self._buffer['Time'] = tm
                self._buffer['Time'] = line
            elif len(line) > 1 and line[0] == 'M':
                _temp = line.split("  ")
                if len(_temp) > 0:
                    _ch = _temp[0].replace("M", '')
                if len(_temp) > 1:
                    _dt = _temp[1]
                    self._buffer[_ch] = _dt
            elif 'END       ' in line:
                self._queue.put_nowait(copy.deepcopy(self._buffer))
                self._buffer = {}
                self._cmd_start()
                break
            else:
                print(line)
    
    def read(self):
        ret = None
        if not self._queue.empty():
            ret = self._queue.get_nowait()
        else:
            # If queue is empty, return None
            ret = None
        return ret


class MainFrame(wx.Frame):
    def __init__(self, parent=None):
        super(MainFrame, self).__init__(parent)
        
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
            self.item_dict["I"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
            self.item_dict["J"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
            self.item_dict["K"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
            self.item_dict["L"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
            self.item_dict["M"]["displacement"] = wx.StaticText(self, label=_label_def, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)

            _bg_colour = wx.Colour("white")
            self.item_dict["I"]["displacement"].SetBackgroundColour(_bg_colour)
            self.item_dict["J"]["displacement"].SetBackgroundColour(_bg_colour)
            self.item_dict["K"]["displacement"].SetBackgroundColour(_bg_colour)
            self.item_dict["L"]["displacement"].SetBackgroundColour(_bg_colour)
            self.item_dict["M"]["displacement"].SetBackgroundColour(_bg_colour)

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
        v_box.Add(incremental_box, 0, wx.EXPAND|wx.ALL, 5)

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
                    _name = "TDS %03d"%ch
                    _label = wx.StaticText(self, label=_name, style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
                    _label.SetFont(_small_font)
                    g_sizer.Add(_label, 1, wx.EXPAND)
                for ch in range(start_ch, start_ch+NUM_DIV):
                    _name = "TDS %03d"%ch
                    _status = wx.StaticText(self, label="0.000", style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
                    _status.SetBackgroundColour(wx.Colour("white"))
                    _status.SetFont(_small_font)
                    g_sizer.Add(_status, 1, wx.EXPAND)
                    self.item_dict["param"][_name] = _status


            _labels = ["I[o____]", "J[_o___]", "K[__o__]", "L[___o_]", "M[____o]", "Time", "Status", "-----", "-----", "-----", ]
            for label in _labels:
                _label = wx.StaticText(self, label=label, style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
                _label.SetFont(_small_font)
                g_sizer.Add(_label, 1, wx.EXPAND)

            _statuss = ["I", "J", "K", "L", "M", "time", "status", "-----", "-----", "-----"]
            for status in _statuss:
                _status = wx.StaticText(self, label="0.000", style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
                _status.SetBackgroundColour(wx.Colour("white"))
                _status.SetFont(_small_font)
                g_sizer.Add(_status, 1, wx.EXPAND)
                if status == "-----":
                    continue
                self.item_dict["param"][status] = _status

            status_box.Add(g_sizer, 0, wx.EXPAND|wx.ALL, 5)
        v_box.Add(status_box, 0, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(v_box)
        self.Layout()

        AsyncBind(wx.EVT_BUTTON, self.button_g91_slow, self.item_dict["button"]["g91_slow"])
        AsyncBind(wx.EVT_BUTTON, self.button_g91_fase, self.item_dict["button"]["g91_fast"])
        AsyncBind(wx.EVT_BUTTON, self.button_g52_set, self.item_dict["button"]["g52_set"])
        AsyncBind(wx.EVT_BUTTON, self.button_gcode_load, self.item_dict["button"]["gcode_load"])
        AsyncBind(wx.EVT_BUTTON, self.button_gcode_start, self.item_dict["button"]["gcode_start"])
        AsyncBind(wx.EVT_BUTTON, self.button_gcode_stop, self.item_dict["button"]["gcode_stop"])
        AsyncBind(wx.EVT_BUTTON, self.button_save_start, self.item_dict["button"]["save_start"])
        AsyncBind(wx.EVT_BUTTON, self.button_save_stop, self.item_dict["button"]["save_stop"])
        #StartCoroutine(self.update_clock, self)
        
    async def button_g91_slow(self, event):
        pass

    async def button_g91_fase(self, event):
        pass

    async def button_g52_set(self, event):
        pass

    async def button_gcode_load(self, event):
        pass

    async def button_gcode_start(self, event):
        # Enable stop button
        self.item_dict["button"]["gcode_stop"].Enable(True)
        # Disable start button
        self.item_dict["button"]["gcode_start"].Enable(False)
        # disable Load button
        self.item_dict["button"]["gcode_load"].Enable(False)
        self.item_dict["button"]["g91_slow"].Enable(False)
        self.item_dict["button"]["g91_fast"].Enable(False)
        self.item_dict["button"]["g52_set"].Enable(False)
        pass

    async def button_gcode_stop(self, event):
        # Enable start button
        self.item_dict["button"]["gcode_start"].Enable(True)
        # Disable stop button
        self.item_dict["button"]["gcode_stop"].Enable(False)
        # Enable Load button
        self.item_dict["button"]["gcode_load"].Enable(True)
        self.item_dict["button"]["g91_slow"].Enable(True)
        self.item_dict["button"]["g91_fast"].Enable(True)
        self.item_dict["button"]["g52_set"].Enable(True)
        pass

    async def button_save_start(self, event):
        # Enable stop button
        self.item_dict["button"]["save_stop"].Enable(True)
        # Disable start button
        self.item_dict["button"]["save_start"].Enable(False)
        # Start saving data
        pass

    async def button_save_stop(self, event):
        # Enable start button
        self.item_dict["button"]["save_start"].Enable(True)
        # Disable stop button
        self.item_dict["button"]["save_stop"].Enable(False)
        # Stop saving data
        pass

    async def update_clock(self):
        while True:
            self.edit_timer.SetLabel(time.strftime('%H:%M:%S'))
            await asyncio.sleep(0.5)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", help="Motor Control Port(Arduino Mega 2560)")
    parser.add_argument("--lport", help="TDS530 Serial Port(TokyoSokki TDS530)")
    args = parser.parse_args()
    
    global ser_reader, ser_writer
    # ser_reader, ser_writer = await serial_asyncio.open_serial_connection(url=args.sport, baudrate=ARDUINO_BAUD_RATE)

    app = WxAsyncApp()
    frame = MainFrame()
    frame.Show()
    app.SetTopWindow(frame)
    await app.MainLoop()


asyncio.run(main())
