#!/usr/bin/python3
import curses
from enum import Enum
from math import ceil
from copy import deepcopy
import functools
import re

def ellipsis(text: str, usable_space: int):
    tooSmall = usable_space < len(text)
    return '' if usable_space == 0 else text[:usable_space - tooSmall] + ('…' if tooSmall else '')

class CDOMStyle:
    def __init__(self, backgroundColor: tuple, wallColor: tuple, titleColor: tuple, textColor: tuple, shadowColor: tuple, highlightedColor: tuple):
        curses.use_default_colors()

        curses.init_pair(1, backgroundColor[0], backgroundColor[1])
        self.backgroundColor = curses.color_pair(1)
        
        curses.init_pair(2, wallColor[0], wallColor[1])
        self.wallColor = curses.color_pair(2)

        curses.init_pair(3, titleColor[0], titleColor[1])
        self.titleColor = curses.color_pair(3)

        curses.init_pair(4, textColor[0], textColor[1])
        self.textColor = curses.color_pair(4)

        curses.init_pair(5, shadowColor[0], shadowColor[1])
        self.shadowColor = curses.color_pair(5)

        curses.init_pair(6, highlightedColor[0], highlightedColor[1])
        self.highlightedColor = curses.color_pair(6)

# Stands for Curses Document Object Model, modeled loosely after the javascript DOM

# CDOM -> window
# page -> document
# element -> element/node

class CDOM:

    # thin wall characters
    PRE_TITLE_CHAR    = '┤'
    POST_TITLE_CHAR   = '├'
    TOP_LEFT_CHAR     = '┌'
    TOP_RIGHT_CHAR    = '┐'
    BOTTOM_LEFT_CHAR  = '└'
    BOTTOM_RIGHT_CHAR = '┘'
    VERTICAL          = '│'
    HORIZONTAL        = '─'
    CROSS             = '🞡'

    # Alternate wall characters
    PRE_TITLE_CHAR    = '╡'
    POST_TITLE_CHAR   = '╞'
    TOP_LEFT_CHAR     = '╔'
    TOP_RIGHT_CHAR    = '╗'
    BOTTOM_LEFT_CHAR  = '╚'
    BOTTOM_RIGHT_CHAR = '╝'
    VERTICAL          = '║'
    HORIZONTAL        = '═'
    CROSS             = '╬'
    LEFT_CONNECT      = '╠'
    RIGHT_CONNECT     = '╣'
    THIN_LEFT_CONNECT = '╟'
    THIN_RIGHT_CONNECT= '╢'
 
    # shadow characters
    SHADOW_BOTTOM     = '▀'
    SHADOW_RIGHT      = '▌'
    SHADOW_BOTTOM_LEFT= '▝'
    SHADOW_TOP_RIGHT  = '▖'
    SHADOW_BOTTOM_RIGHT='▘'
    # 3 is the length/2 of the title's padding: '┌┤  ├┐'
    MIN_TITLE_PADDING = 3

    # I need a better way of passing colors
    def __init__(self, stdscr, style):
        self.pages = []
        self.stdscr = stdscr

        self.style = style

        self.height = 0
        self.width = 0
        self.displayLine = 0

        self.logString = ''

        self.history = []

    def addPages(self, *pages):
        for page in pages:
            page.setCDOM(self)
            self.pages.append(page)
    
    def loadPage(self, url: str, fromHistoryPage = False):
        # find page with matching url
        page = [page for page in self.pages if page.url == url]

        if len(page) == 0:
            return None
        
        page = page[0].copy() if page[0].stateless else page[0]

        # load elements and page
        for element in page.elements:
            if element.onload is not None:
                element.onload(element)
        
        if page.onload is not None:
            page.onload(page)

        return page

    def goToPage(self, url: str, fromHistoryPage = False):
        # get page from url
        page = self.loadPage(url, fromHistoryPage)

        if not page:
            return False

        # unload the current page if there is one
        if hasattr(self, 'currentPage'):
            if not fromHistoryPage:
                self.history.append(self.currentPage.url)

            for element in self.currentPage.elements:
                if element.onunload is not None:
                    element.onunload(element)
            
            if self.currentPage.onunload is not None:
                self.currentPage.onunload(self.currentPage)

        # set current page and return True
        self.currentPage = page
        return True
    
    def goHome(self):
        if not self.goToPage('home'):
            self.goToPage(self.pages[0].url)
    
    def log(self, string):
        self.logString = str(string)

    def trystr(self, row, col, string, color):
        try:
            self.stdscr.addstr(row, col, string, color)
        except curses.error:
            pass

    # normal call: pass in currentPage, height and width of terminal, it will render to fit
    def renderPage(self, page, height: int, width: int, top = None, left = None):
        self.height = height
        self.width = width

        if height == 0 or width == 0:
            return

        # remove elements that aren't to be displayed
        elements = [elem for elem in page.elements if elem.style.display]

        # clear background
        try:
            self.stdscr.bkgd(' ', self.style.backgroundColor)
        except curses.error:
            pass

        if not page.highlightedElement:
            page.selectNext()

        # call page and each element's onrefresh method if they have one
        for element in elements:
            if element.onrefresh:
                element.onrefresh(element)
        
        if page.onrefresh:
            page.onrefresh(page)

        # calculate size of page
        if page.size[0] is None:
            pageHeight = functools.reduce(lambda acc, elem: acc + elem.displayHeight(), elements, 0) + page.style.margin[0] * 2
        elif page.size[0] <= 0:
            pageHeight = height + page.size[0] * 2
        else:
            pageHeight = page.size[0]

        pageWidth = 0

        if page.size[1] is None:
            for element in elements:
                if element.displayWidth() > pageWidth:
                    pageWidth = element.displayWidth() + page.style.margin[1] * 2
                
            if len(page.title) > pageWidth and page.style.border:
                pageWidth = len(page.title) + CDOM.MIN_TITLE_PADDING * 2
        elif page.size[1] <= 0:
            pageWidth = width + page.size[1] * 2
        else:
            pageWidth = page.size[1]

        # calculate useful constants
        usableWidth = min(width, pageWidth)
        usableHeight = min(height, pageHeight)
        
        textspace = max(0, usableWidth - page.style.margin[1] * 2)
        linespace = max(0, usableHeight - page.style.margin[0] * 2)

        top = top or max(0, (height - pageHeight) // 2)
        left = left or max(0, (width - pageWidth) // 2)

        page.displaySize = (usableHeight, usableWidth)

        # draw page shadow
        if page.style.shadow:
            self.trystr(top + usableHeight + page.style.border, left + (not page.style.border), self.SHADOW_BOTTOM * (usableWidth - 1 + 2 * page.style.border - (page.style.border and width <= pageWidth)), self.style.shadowColor)

            self.trystr(top - page.style.border, left + pageWidth + page.style.border, self.SHADOW_TOP_RIGHT, self.style.shadowColor)
            
            for line in range(usableHeight - 1 + 2 * page.style.border):
                self.trystr(top + line + (not page.style.border), left + pageWidth + page.style.border, self.SHADOW_RIGHT, self.style.shadowColor)
            
            self.trystr(top + usableHeight + page.style.border, left - page.style.border, self.SHADOW_BOTTOM_LEFT, self.style.shadowColor)
        
            self.trystr(top + usableHeight + page.style.border, left + usableWidth + page.style.border, self.SHADOW_BOTTOM_RIGHT, self.style.shadowColor)
            

        if height >= 1:
            # draw page border and title
            if page.style.border:
                preTitle = [
                    '',
                    CDOM.CROSS,
                    CDOM.HORIZONTAL + CDOM.CROSS,
                    CDOM.HORIZONTAL + CDOM.CROSS,
                    CDOM.HORIZONTAL + CDOM.PRE_TITLE_CHAR,
                    CDOM.HORIZONTAL + CDOM.PRE_TITLE_CHAR + ' ',
                    CDOM.HORIZONTAL + CDOM.PRE_TITLE_CHAR + ' '
                ][min(6, width)] if width <= 6 + len(page.title) else CDOM.HORIZONTAL * (((usableWidth + 2 - len(page.title)) // 2) - 3) + CDOM.PRE_TITLE_CHAR + ' '
                postTitle = [
                    '',
                    CDOM.HORIZONTAL,
                    CDOM.POST_TITLE_CHAR + CDOM.HORIZONTAL,
                    ' ' + CDOM.POST_TITLE_CHAR + CDOM.HORIZONTAL
                ][min(6, width) // 2] if width <= 6 + len(page.title) else ' ' + CDOM.POST_TITLE_CHAR + CDOM.HORIZONTAL * (ceil((usableWidth + 2 - len(page.title)) / 2) - 3)

                title = ellipsis(page.title, max(0, usableWidth - CDOM.MIN_TITLE_PADDING * 2))

                for line in range(top, top + usableHeight):
                    if width > pageWidth + 1:
                        self.trystr(line, left - 1, CDOM.VERTICAL, self.style.wallColor)
                    if width > pageWidth:
                        self.trystr(line, left + usableWidth, CDOM.VERTICAL, self.style.wallColor)
                
                if height > pageHeight + 1:
                    self.trystr(top - 1, left, preTitle, self.style.wallColor)
                    self.trystr(top - 1, left + len(preTitle), title, self.style.titleColor | curses.A_BOLD)
                    self.trystr(top - 1, left + len(preTitle + title), postTitle, self.style.wallColor)

                if height > pageHeight:
                    self.trystr(top + usableHeight, left, CDOM.HORIZONTAL * usableWidth, self.style.wallColor)

                # try corners
                self.trystr(top - 1, left - 1, CDOM.TOP_LEFT_CHAR, self.style.wallColor)
                self.trystr(top - 1, left + usableWidth, CDOM.TOP_RIGHT_CHAR, self.style.wallColor)
                self.trystr(top + usableHeight, left - 1, CDOM.BOTTOM_LEFT_CHAR, self.style.wallColor)
                self.trystr(top + usableHeight, left + usableWidth, CDOM.BOTTOM_RIGHT_CHAR, self.style.wallColor)

            # draw background for page
            for line in range(usableHeight):
                self.trystr(top + line, left, ' ' * usableWidth, self.style.textColor)
            
            # if ain't no elems, don't render ya dummy !
            if len(elements) == 0:
                return

            totalLines = functools.reduce(lambda acc, elem: acc + elem.displayHeight(), elements, 0)

            # get the line offset of the highlighted element and adjust displayLine to fit it
            if page.highlightedElement:
                highlightedLine = 1
                
                for i in range(page.highlightedElement.index()):
                    highlightedLine += page.elements[i].displayHeight()

                if highlightedLine - self.displayLine >= linespace - 1:
                    self.displayLine = min(highlightedLine + 1 - linespace, totalLines - linespace)
                elif highlightedLine < self.displayLine + 2:
                    self.displayLine = max(highlightedLine - 2, 0)

            currentLine = 0

            for elem in elements:
                for line in elem.lines():

                    if currentLine >= self.displayLine:

                        unhighlighted_color = self.style.textColor
                        x = page.style.margin[1]

                        string = ''

                        if currentLine < linespace + self.displayLine:
                            if (currentLine - self.displayLine == linespace - 1 and currentLine != totalLines - 1) or (currentLine == self.displayLine and self.displayLine != 0):
                                string = '…'
                            else:
                                string = line

                                x += [
                                    elem.style.indent,
                                    (textspace - len(string)) // 2,
                                    textspace - len(string) - elem.style.indent
                                ][elem.style.align.value]

                                unhighlighted_color = (self.style.textColor if not elem.style.color else curses.color_pair(elem.style.color)) | elem.style.weight

                        string = ellipsis(string, textspace - elem.style.indent)

                        if elem is page.highlightedElement:
                            self.trystr(top + currentLine + page.style.margin[0] - self.displayLine, left + x, string, self.style.highlightedColor | elem.style.weight | curses.A_BOLD)
                        else:
                            self.trystr(top + currentLine + page.style.margin[0] - self.displayLine, left + x, string, unhighlighted_color or self.style.textColor | elem.style.weight)

                    currentLine += 1

        self.stdscr.move(0, 0)
        self.trystr(0, 0, self.logString, self.style.shadowColor)
         
        # Refresh the screen
        self.stdscr.refresh()

class PageStyle():
    def __init__(self, border = True, margin = (1, 1), shadow = True):
        self.border = border
        self.margin = margin
        self.shadow = shadow

class Page:
    def __init__(self, url: str, title: str, elements: list, size: tuple = (None, None), style: PageStyle = PageStyle(), data: dict = {}, stateless = True, onload = None, onunload = None, onrefresh = None):
        self.url = url
        self.title = title
        self.size = size
        self.displaySize = (0, 0)
        self.style = style
        self.elements = elements
        self.data = data
        self.stateless = stateless
        self.onload = onload
        self.onunload = onunload
        self.onrefresh = onrefresh

        self.highlightedElement = None
        self.selectNext()

    def copy(self):
        cp = Page(
            url=self.url[:],
            title=self.title[:],
            size=self.size + tuple(),
            style=deepcopy(self.style),
            elements=[elem.copy() for elem in self.elements],
            data=deepcopy(self.data),
            stateless=self.stateless,
            onload=self.onload,
            onunload=self.onunload,
            onrefresh=self.onrefresh
        )

        cp.setCDOM(self.cdom)

        return cp

    def setCDOM(self, cdom: CDOM):
        self.cdom = cdom

        for element in self.elements:
            element.cdom = cdom
            element.page = self
    
    def selectPrevious(self):
        start = 0 if self.highlightedElement is None else (self.elements.index(self.highlightedElement) - 1)
        length = len(self.elements)

        for i in range(start + length, start, -1):
            i %= length
            elem = self.elements[i]

            if isinstance(elem, Selectable) and elem.style.display:
                self.highlightedElement = self.elements[i]
                return
        
        self.highlightedElement = None

    def selectNext(self):
        start = 0 if self.highlightedElement is None else (self.elements.index(self.highlightedElement) + 1)
        length = len(self.elements)

        for i in range(start, start + length):
            i %= length
            elem = self.elements[i]

            if isinstance(elem, Selectable) and elem.style.display:
                self.highlightedElement = self.elements[i]
                return

        self.highlightedElement = None

    def getElementByID(self, ID: str):
        for elem in self.elements:
            if elem.ID == ID:
                return elem
        
    def getElementsByClassName(self, className: str):
        res = []

        for element in self.elements:
            if className in element.classList:
                res.append(element)

        return res
    
    def addElements(self, elements: list, index: int = -1):
        if index == -1:
            index = len(self.elements)
        
        for element in elements:
            element.cdom = self.cdom
            element.page = self

            self.elements.insert(index, element)
            index += 1

            if element.onload is not None:
                element.onload(element)

    def addElement(self, element, index: int = -1):
        self.addElements([ element ], index)
    
    def removeElements(self, elements):
        for element in elements:
            self.removeElement(element)
    
    def removeElement(self, element):
        if element is self.highlightedElement:
            self.selectPrevious()

        self.elements.remove(element)

class Align(Enum):
    LEFT   = 0
    CENTER = 1
    RIGHT  = 2

class Style:
    def __init__(self, color = None, align: Align = Align.LEFT, weight = curses.A_NORMAL, indent: int = 0, display = True, height = None, displayIndex: int = 0):
        self.color = color
        self.align = align
        self.weight = weight
        self.indent = indent
        self.display = display
        self.height = height
        self.displayIndex = displayIndex

class Element:
    def __init__(self, text: str = '', style: Style = Style(), ID: str = '', classList: list = [], data: dict = {}, onrefresh = None, onload = None, onunload = None):
        self.text = text
        self.style = style
        self.ID = ID
        self.classList = classList
        self.onload = onload
        self.onunload = onunload
        self.onrefresh = onrefresh
        self.page = None

        self.data = data
    
    def copy(self):
        return Element(
            text=self.text[:],
            style=deepcopy(self.style),
            ID=self.ID[:],
            classList=self.classList[:],
            data=deepcopy(self.data),
            onload=self.onload,
            onunload=self.onunload,
            onrefresh=self.onrefresh
        )

    def index(self):
        return self.page.elements.index(self)
    
    def lines(self):
        lines = self.text.split('\n')[self.style.displayIndex:]

        if self.style.height:
            if len(lines) > self.style.height:
                lines = lines[:self.style.height]
            else:
                lines.extend([''] * max(0, self.style.height - len(lines)))

        return lines
    
    def getText(self):
        return [
            ' ' * self.style.indent + self.text,
            self.text,
            self.text + ' ' * self.style.indent
        ][self.style.align.value]

    def displayHeight(self):
        return self.style.height or len(self.lines())

    def displayWidth(self):
        return len(self.getText())

class Break(Element):
    def __init__(self, ID: str = ''):
        super().__init__(ID=ID)

    def copy(self):
        return Break(ID=self.ID[:])

class Linebreak(Element):
    def __init__(self, char: str = '━', ID: str = ''):
        super().__init__(ID=ID, onrefresh=Linebreak.defaultOnrefresh)

        self.char = char

    @staticmethod
    def defaultOnrefresh(this):
        this.text = (this.page.displaySize[1] - 2) * this.char

    def copy(self):
        return Linebreak(ID=self.ID[:], char=self.char[:])

class Wallbreak(Linebreak):
    def __init__(self, ID: str = ''):
        super().__init__(ID=ID, char='═')

    def copy(self):
        return Wallbreak(ID=self.ID[:])

class ThinWallbreak(Linebreak):
    def __init__(self, ID: str = ''):
        super().__init__(ID=ID, char='─')

    def copy(self):
        return ThinWallbreak(ID=self.ID[:])

class Selectable(Element):
    def __init__(self, text: str = '', style: Style = Style(), ID: str = '', classList: list = [], data: dict = {}, onrefresh = None, onload = None, onunload = None, onkey = None, onselect = None):
        super().__init__(text, style, ID, classList, data, onrefresh, onload, onunload)

        self.onkey = onkey
        self.onselect = onselect
    
    def copy(self):
        return Selectable(
            text=self.text[:],
            style=deepcopy(self.style),
            ID=self.ID[:],
            classList=self.classList[:],
            data=deepcopy(self.data),
            onload=self.onload,
            onunload=self.onunload,
            onkey=self.onkey,
            onrefresh=self.onrefresh,
            onselect=self.onselect
        )
    
class Link(Selectable):
    def __init__(self, label: str = '', style: Style = Style(), ID: str = '', classList: list = [], data: dict = {}, onrefresh = None, onload = None, onunload = None, onkey = None, onselect = None, url: str = ''):
        super().__init__('', style, ID, classList, data, onrefresh, onload, onunload, onkey, onselect)

        self.label = label
        self.url = url
        self.onload = Link.defaultOnload

    def copy(self):
        return Link(
            label=self.label[:],
            style=deepcopy(self.style),
            ID=self.ID[:],
            classList=self.classList[:],
            data=deepcopy(self.data),
            onload=self.onload,
            onunload=self.onunload,
            onkey=self.onkey,
            onrefresh=self.onrefresh,
            onselect=self.onselect,
            url=self.url[:]
        )

    @staticmethod
    def defaultOnload(this):
        this.updateText()

    def updateText(self):
        self.text = self.label + ' →'

class Input(Selectable):
    def __init__(self, text: str = '', style: Style = Style(), ID: str = '', classList: list = [], data: dict = {}, onrefresh = None, onload = None, onunload = None, onkey = None, onselect = None, value = '', label = '', boxed = True):
        super().__init__(text, style, ID, classList, data, onrefresh, onload, onunload, onkey, onselect)

        self.selected = False
        self.value = value
        self.label = label
        self.boxed = boxed
        self.onrefresh = Input.defaultOnrefresh if onrefresh is None else onrefresh
        self.onkey = Input.defaultOnkey if onkey is None else onkey

    def copy(self):
        return Input(
            text=self.text[:],
            style=deepcopy(self.style),
            ID=self.ID[:],
            classList=self.classList[:],
            data=deepcopy(self.data),
            onload=self.onload,
            onunload=self.onunload,
            onkey=self.onkey,
            onrefresh=self.onrefresh,
            onselect=self.onselect,
            value=self.value[:] if type(self.value) is str else self.value,
            label=self.label[:],
            boxed=self.boxed
        )
    @staticmethod
    def defaultOnrefresh(this):
        this.updateText()

        if this.selected:
            this.style.weight = curses.A_UNDERLINE
        else:
            this.style.weight = curses.A_NORMAL

    @staticmethod
    def defaultOnkey(this, e):
        k = e.key

        if this.selected:
            char = curses.keyname(k).decode('utf-8')

            e.preventDefault()

            if len(char) == 1:
                this.value += char

            if k == curses.KEY_BACKSPACE:
                this.value = this.value[:-1]
            elif k == 27:
                this.selected = False
        
        if k == curses.KEY_ENTER or k == 10 or k == 13:
            this.selected = not this.selected

        this.updateText()
    
    def updateText(self):
        self.text = f"{self.label}{': ' * (self.label != '')}{'[' * self.boxed}{self.value}{']' * self.boxed}"

class Dropdown(Input):
    def __init__(self, text: str = '', style: Style = Style(), ID: str = '', classList: list = [], data: dict = {}, onrefresh = None, onload = None, onunload = None, onkey = None, onselect = None, value = '', label = '', boxed = True, valueList=[]):
        super().__init__(text, style, ID, classList, data, onrefresh, onload, onunload, onkey, onselect, value, label, boxed)

        if value == '':
            self.value = valueList[0]
        
        self.valueList = valueList
        self.onkey = Dropdown.defaultOnkey if onkey is None else onkey

    def copy(self):
        return Dropdown(
            text=self.text[:],
            style=deepcopy(self.style),
            ID=self.ID[:],
            classList=self.classList[:],
            data=deepcopy(self.data),
            onload=self.onload,
            onunload=self.onunload,
            onkey=self.onkey,
            onrefresh=self.onrefresh,
            onselect=self.onselect,
            value=self.value[:] if type(self.value) is str else self.value,
            label=self.label[:],
            boxed=self.boxed,
            valueList=self.valueList[:]
        )

    @staticmethod
    def defaultOnkey(this, e):
        k = e.key

        if this.selected:
            e.preventDefault()

            if k == curses.KEY_DOWN:
                i = this.valueList.index(this.value)

                if i == len(this.valueList) - 1:
                    i = -1
                
                this.value = this.valueList[i + 1]
            elif k == curses.KEY_UP:
                i = this.valueList.index(this.value)

                if i == 0:
                    i = len(this.valueList)
                
                this.value = this.valueList[i - 1]
            elif k == 27:
                this.selected = False
        
        if k == curses.KEY_ENTER or k == 10 or k == 13:
            this.selected = not this.selected

        this.updateText()

class Checkbox(Selectable):
    def __init__(self, label: str = '', style: Style = Style(), ID: str = '', classList: list = [], data: dict = {}, onrefresh = None, onload = None, onunload = None, onkey = None, onselect = None, checked = False):
        super().__init__('', style, ID, classList, data, onrefresh, onload, onunload, onkey, onselect)

        self.checked = checked
        self.label = label
        
        self.onselect = Checkbox.defaultOnselect if onselect is None else onselect

        self.updateText()

    @staticmethod
    def defaultOnselect(this):
        this.checked = not this.checked

        this.updateText()
    
    def copy(self):
        return Checkbox(
            label=self.label[:],
            style=deepcopy(self.style),
            ID=self.ID[:],
            classList=self.classList[:],
            data = deepcopy(self.data),
            onrefresh=self.onrefresh,
            onload=self.onload,
            onunload=self.onunload,
            onkey=self.onkey,
            onselect=self.onselect,
            checked=self.checked
        )

    def updateText(self):
        self.text = f"{self.label}: [{'✓' if self.checked else ' '}]"


class Event():
    def __init__(self):
        self.canceled = False

    def preventDefault(self):
        self.canceled = True

class KeyEvent(Event):
    def __init__(self, key):
        super().__init__()

        self.key = key