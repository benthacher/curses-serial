import serial
import time
import threading

def currentTime():
    return int(round(time.time() * 1000))

class SerialConnection:
    def __init__(self):
        self.port = None
        self.baudrate = 9600
        self.showTime = False

        self.thread = None
        self.ser = None

        self.startTime = 0
    
    def connect(self, page):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=5, write_timeout=5)

            self.stillAlive = True
            self.output = True

            self.thread = threading.Thread(target=self.readPort, args=[ page ])
            self.thread.start()

            self.startTime = currentTime()

            page.title = self.port

        except KeyboardInterrupt:
            self.disconnect(page)

    def readPort(self, page):
        try:

            serialData = page.getElementByID('serial-data')
            
            if self.showTime and self.output:
                serialData.text += "[{}] ".format(format(currentTime() - self.startTime, '07'))

            while self.stillAlive:
                try:
                    if self.output:
                        data = self.ser.read(5).decode('utf-8')

                        for char in data:
                            serialData.text += char

                            if char == '\n' and self.showTime:
                                serialData.text += "[{}] ".format(format(currentTime() - self.startTime, '07'))

                        if page.displaySize[0] - (3 + page.style.margin[0] * 2) < serialData.displayHeight():
                            serialData.style.displayIndex += 1
                    
                except (UnicodeDecodeError, serial.serialutil.SerialException):
                    pass

        except serial.SerialTimeoutException:

            serialData.text += 'Serial timeout while trying to receive data.'

            self.disconnect(page)
        
    def send(self, string):
        if self.stillAlive:
            print(string)
            self.ser.write(string.encode('utf-8'))
    
    def disconnect(self, page):
        self.stillAlive = False
        self.ser.close()

        page.getElementByID('serial-data').text += 'Detached from ' + self.ser.name    
