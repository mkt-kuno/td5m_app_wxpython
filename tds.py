import copy
import asyncio
import aioserial
import datetime

class TDS530:
    def __init__(self, port = '/dev/ttyUSB0', baudrate = 38400):
        self._com:aioserial.AioSerial = aioserial.AioSerial(port=port, baudrate=baudrate)
        self._com.reset_input_buffer()
        self._lock = asyncio.Lock()
        self._data = {}
        self._task = None

    async def _cmd_start(self):
        self._com.reset_input_buffer()
        self._com.reset_output_buffer()
        await self._com.write_async('ST\r\n'.encode('ascii'))

    def start(self):
        if self._task is not None:
            return
        self._task = asyncio.create_task(self.task())

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def read(self):
        ret = {}
        async with self._lock:
            ret = copy.deepcopy(self._data)
        return ret

    async def task(self):
        _temp = {}

        while True:
            await self._cmd_start()

            # Read Time
            while True:
                line = await self._com.readline_async()
                line = line.decode().replace('\r\n', '')
                if line == "":
                    continue
                _dt = datetime.datetime.strptime(line, "%Y/%m/%d %H:%M:%S")
                _temp['time'] = _dt
                break       

            # Read Ch Value
            while True:
                line = await self._com.readline_async()
                line = line.decode().replace('\r\n', '')
                if line == "":
                    continue

                # if END recv, break, goto next loop
                if "END" in line:
                    async with self._lock:
                        self._data = copy.deepcopy(_temp)    
                    _temp = {}
                    break
            
                _param = line.split("  ")
                _ch = int(_param[0].replace("M", ''))
                _dt = float("nan")
                try:
                    _dt = float(_param[1])
                except:
                    pass
                _temp["%03d"%_ch] = _dt

async def main():
    logger = TDS530()
    # 初回開始時にはStart
    await logger.start()
    while True:
        # 定期的に呼ぶ
        ret = await logger.read()
        if ret is not None:
            print(ret)
            pass
        await asyncio.sleep(0.5)

if __name__ == '__main__':
    asyncio.run(main())