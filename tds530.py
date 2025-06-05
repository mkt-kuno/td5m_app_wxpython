import copy
import serial
#from icecream import ic

class TDS530:
    def __init__(self, port = '/dev/ttyUSB0', baudrate = 38400, timeout=0.1):
        self._com = serial.Serial(port, baudrate, timeout=timeout)
        self._com.reset_input_buffer()
        self._buffer = {}

    def start(self):
        self._com.reset_input_buffer()
        self._com.reset_output_buffer()
        self._com.write('ST\r\n'.encode('ascii'))

    def _cmd_start(self):
        self._com.reset_input_buffer()
        self._com.reset_output_buffer()
        self._com.write('ST\r\n'.encode('ascii'))

    def read(self):
        ret = None
        while (self._com.readable()):
            line = self._com.readline()
            ch = dt = temp = None
            if line is None:
                break
            line = line.decode('ascii').replace('\r\n', '')
            if line == '':
                break
            if "ERR" in line:
                print("ERROR")
                # @todo もしエラーが出てしまうなら考慮する
            elif len(line) > 1 and line[0] == '2':
                # Time型表記
                #tm = time.strptime(line, '%Y/%d/%m %H:%M:%S')
                #self._buffer['Time'] = tm
                self._buffer['Time'] = line
            elif len(line) > 1 and line[0] == 'M':
                temp = line.split("  ")
                if len(temp) > 0:
                    ch = temp[0].replace("M", '')
                if len(temp) > 1:
                    dt = temp[1]
                    self._buffer[ch] = dt
            elif 'END       ' in line:
                ret = copy.deepcopy(self._buffer)
                self._buffer = {}
                self._cmd_start()
                break
            else:
                print(line)
        return ret            


if __name__ == '__main__':
    logger = TDS530()
    # 初回開始時にはStart
    logger.start()
    while True:
        # 定期的に呼ぶ
        ret = logger.read()
        if ret is not None:
            print(ret)

