import curses

from page import Page, PageStyle
from element import Element, Style, Align, Selectable, Link, Break, Wallbreak, Input, Dropdown, Checkbox
from connection import SerialConnection, currentTime
from event import KeyEvent

import subprocess
import re

import serial.tools.list_ports

customBaudrate = False
startTime = 0

connection = SerialConnection()

def select_port(this, e):
    connection.port = this.ID

def set_values(this, e):
    page = this.page

    connection.baudrate = page.getElementByID('baudrate').value if not customBaudrate else page.getElementByID('baudrate-custom').value
    connection.showTime = page.getElementByID('show-time').checked

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

def send_data(this, e):
    if this.value != '' and not this.selected:
        connection.send(this.value)

        this.value = ''

        this.selected = True

def toggle_custom_baudrate(this, e):
    global customBaudrate

    custom = this.page.getElementByID('baudrate-custom')
    baudrate = this.page.getElementByID('baudrate')

    custom.style.display = not custom.style.display
    baudrate.style.display = not baudrate.style.display

    customBaudrate = not customBaudrate

def toggle_output(this, e):
    if KeyEvent.isEnter(e.key):
        this.text = 'Resume Output (use arrow keys to traverse output)' if connection.output else 'Pause Output'
        connection.output = not connection.output
    
    if not connection.output:
        dataElem = this.page.getElementByID('serial-data')

        if 'scrollVelocity' in dataElem.data.keys():
            if currentTime() - dataElem.data.get('prevTime', 0) < 100:
                dataElem.data['scrollVelocity'] += 0.1
            else:
                dataElem.data['scrollVelocity'] = 1

            vel = dataElem.data['scrollVelocity']
        else:
            dataElem.data['scrollVelocity'] = vel = 1
        
        maxheight = len(dataElem.text.split('\n')) - 1

        if e.key == curses.KEY_UP:
            dataElem.style.displayIndex -= int(1 * vel) if dataElem.style.displayIndex > 0 else 0
            e.preventDefault()
        if e.key == curses.KEY_DOWN:
            dataElem.style.displayIndex += int(1 * vel) if dataElem.style.displayIndex < maxheight else 0
            e.preventDefault()
        if e.key == curses.KEY_PPAGE:
            dataElem.style.displayIndex = dataElem.style.displayIndex - int(10 * vel) if dataElem.style.displayIndex > 10 else 0
            e.preventDefault()
        if e.key == curses.KEY_NPAGE:
            dataElem.style.displayIndex = dataElem.style.displayIndex + int(10 * vel) if dataElem.style.displayIndex < maxheight - 1 else maxheight
            e.preventDefault()
        
        dataElem.style.displayIndex = max(dataElem.style.displayIndex, 0)
        dataElem.style.displayIndex = min(dataElem.style.displayIndex, maxheight)
        
        dataElem.data['prevTime'] = currentTime()

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
        size=(None, 40),
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
                ID='custom-baudrate',
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
                label='Send',
                ID='send-input',
                boxed=False,
                onselect=send_data
            ),
            Selectable(
                text='Pause Output',
                onkey=toggle_output
            ),
            Wallbreak(),
            Element(ID='serial-data')
        ],
        onload=connection.connect,
        onunload=connection.disconnect
    )
]