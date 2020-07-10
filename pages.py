import curses

from page import Page, PageStyle
from element import Element, Style, Align, Selectable, Link, Break, Wallbreak, Input, Dropdown, Checkbox

import subprocess
import re

import serial
import serial.tools.list_ports
import time
import threading

def currentTime():
    return int(round(time.time() * 1000))

mainStillRunning = True
selectedPort = ''
selectedBaudrate = 0
customBaudrate = False
showTime = False
startTime = 0
ser = None

def select_port(this, e):
    global selectedPort
    
    selectedPort = this.ID

def set_values(this, e):
    global selectedBaudrate, showTime

    page = this.page

    selectedBaudrate = page.getElementByID('baudrate').value if not customBaudrate else page.getElementByID('baudrate-custom').value
    showTime = page.getElementByID('show-time').checked

def load_serial_ports(page):
    devices = [tuple(p) for p in list(serial.tools.list_ports.comports())]

    for devData in devices:
        port = devData[0]
        name = devData[1]

        link = Link(
            label=port + ' ' + name,
            ID=port,
            url='serial-port-settings',
            onselect=select_port
        )

        page.addElement(link)

        link.updateText()

def load_port(page):
    global ser, startTime

    page.title = selectedPort
    ser = serial.Serial(selectedPort, selectedBaudrate)

    startTime = currentTime()

    threading.Thread(target=read_from_port, args=[ page ]).start()

def close_port(page):
    global mainStillRunning

    ser.close()
    mainStillRunning = False

def read_from_port(page):
    try:
        serialData = page.getElementByID('serial-data')

        while mainStillRunning:
            
            if showTime:
                serialData.text += "[{}] ".format(format(currentTime() - startTime, '07'))

            try:
                serialData.text += ser.read().decode('utf-8')
            except UnicodeDecodeError:
                pass

    except KeyboardInterrupt:
        page.addElement(Element(text='Detached from ' + ser.name))
        ser.close()

def send_data(this):
    input = this.page.getElementByID('send-input')

    if input.value != '':
        ser.write(input.value)
    
        input.value = ''

def toggle_custom_baudrate(this, e):
    global customBaudrate

    custom = this.page.getElementByID('baudrate-custom')
    baudrate = this.page.getElementByID('baudrate')

    custom.style.display = not custom.style.display
    baudrate.style.display = not baudrate.style.display

    customBaudrate = not customBaudrate

pages = [
    # Page(
    #     url='home',
    #     title='test',
    #     size=(10, 40),
    #     style=PageStyle(
    #         margin=(2, 2)
    #     ),
    #     elements=[Selectable(text=str(i)) for i in range(10)]
    # ),
    Page(
        url='home',
        title='Serial TUI',
        size=(10, 40),
        elements=[
            Element(
                text='Select an option',
                style=Style(
                    align=Align.CENTER,
                    weight=curses.A_BOLD
                )
            ),
            Break(),
            Link(
                label='Open Serial Port',
                url='serial-port-select'
            ),
            Break(),
            Break(),
            Selectable(
                text='Quit',
                onselect=lambda this, e: quit()
            )
        ],
        stateless=False
    ),
    Page(
        url='serial-port-select',
        title='Select a Serial Port',
        size=(None, None),
        elements=[],
        onload=load_serial_ports
    ),
    Page(
        url='serial-port-settings',
        title='Settings',
        size=(None, None),
        elements=[
            Element(
                text='Baudrate'
            ),
            Input(
                value='',
                style=Style(
                    display=False,
                    indent=2
                ),
                label='',
                ID='baudrate-custom'
            ),
            Dropdown(
                valueList=[115200, 57600, 38400, 19200, 9600, 4800, 2400, 1800, 1200, 600, 300, 200, 150, 134, 110, 75, 50],
                value=9600,
                style=Style(
                    indent=2
                ),
                label='',
                ID='baudrate'
            ),
            Checkbox(
                label='Custom Baudrate',
                style=Style(
                    indent=2
                ),
                ID='show-time',
                onselect=toggle_custom_baudrate
            ),
            Checkbox(
                label='Show time',
                ID='show-time'
            ),
            Link(
                label='Connect',
                url='serial-port',
                onselect=set_values
            )
        ],
        stateless=False
    ),
    Page(
        url='serial-port',
        title='serial port name',
        size=(-2, -2),
        elements=[
            Input(
                label='λ',
                ID='send-input',
                boxed=False
            ),
            Wallbreak(),
            Element(ID='serial-data')
        ],
        onload=load_port,
        onunload=close_port
    )
]