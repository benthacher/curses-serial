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
        self.ser = serial.Serial(self.port, self.baudrate, timeout=5, write_timeout=5)

        self.still_alive = True

        self.thread = threading.Thread(target=self.readPort, args=[ page ])
        self.thread.start()

        self.startTime = currentTime()

        page.title = self.port

    def readPort(self, page):
        try:
            serialData = page.getElementByID('serial-data')

            while self.still_alive:

                if self.showTime:
                    serialData.text += "[{}] ".format(format(currentTime() - self.startTime, '07'))

                try:
                    serialData.text += self.ser.read().decode('utf-8')
                except UnicodeDecodeError:
                    pass

        except KeyboardInterrupt:

            serialData.text += 'Detached from ' + self.ser.name

            self.still_alive = False
            self.ser.close()

        except serial.SerialTimeoutException:

            serialData.text += 'Serial timeout while trying to receive data.'

            self.still_alive = False
            self.ser.close()
        
    def send(self, string):
        if self.still_alive:
            print(string)
            self.ser.write(string.encode('utf-8'))
    
    def disconnect(self, page):
        self.still_alive = False
        self.ser.close()

        page.getElementByID('serial-data').text = ''
