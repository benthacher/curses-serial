import sys,os
import curses

from cdom import CDOM, Link, KeyEvent
import pages

from enum import Enum

def draw_menu(stdscr):
    k = 0
    
    stdscr.clear()
    stdscr.refresh()

    stdscr.nodelay(1)

    curses.curs_set(0)

    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_MAGENTA)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_YELLOW)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_CYAN)

    curses.mousemask(1)

    cdom = CDOM(stdscr, 
        backgroundColor  = curses.color_pair(1),
        titleColor       = curses.color_pair(2),
        textColor        = curses.color_pair(3),
        highlightedColor = curses.color_pair(4),
        wallColor        = curses.color_pair(5),
        shadowColor      = curses.color_pair(6))

    cdom.addPages(*pages.pages)

    cdom.goHome()

    while (True):

        k = stdscr.getch()

        height, width = stdscr.getmaxyx()

        highlighted = cdom.currentPage.highlightedElement

        if k != -1:

            if k == curses.KEY_LEFT:
                if cdom.history:
                    cdom.goToPage(cdom.history.pop(), True)
            
            # if no highlighted element, nothing below matters
            if not highlighted:
                continue

            # make key event with k
            e = KeyEvent(k)

            # if element has a custom onkey function, run it with e
            if highlighted.onkey:
                highlighted.onkey(highlighted, e)

            # if e.preventDefault has been called, prevent default
            if e.canceled:
                continue

            # default key events
            if k == curses.KEY_UP:
                cdom.currentPage.selectPrevious()
            elif k == curses.KEY_DOWN:
                cdom.currentPage.selectNext()
            elif k == curses.KEY_ENTER or k == 10 or k == 13:
                if highlighted.onselect:
                    highlighted.onselect(highlighted)
            
                if isinstance(highlighted, Link):
                    cdom.goToPage(highlighted.url)
            elif k == curses.KEY_RIGHT:
                if isinstance(highlighted, Link):
                    if highlighted.onselect:
                        highlighted.onselect(highlighted)
                    
                    cdom.goToPage(highlighted.url)
        
        cdom.renderPage(cdom.currentPage, height, width)

        curses.delay_output(16)

def main():
    curses.wrapper(draw_menu)

if __name__ == '__main__':
    os.system('cat ~/.cache/wal/sequences')
    main()
