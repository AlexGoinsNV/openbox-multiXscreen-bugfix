###########################################################################
###          Functions for helping out with your window focus.          ###
###########################################################################

###########################################################################
###         Options that affect the behavior of the focus module.       ###
###                                                                     ###
# raise the window also when it is focused                              ###
cycle_raise = 1                                                         ###
# raise as you cycle in stacked mode                                    ###
stacked_cycle_raise = 0                                                 ###
# show a pop-up list of windows while cycling                           ###
stacked_cycle_popup_list = 1                                            ###
# send focus somewhere when nothing is left with the focus, if possible ###
fallback = 0                                                            ###
###                                                                     ###
###                                                                     ###
# Provides:                                                             ###
# def focus_next_stacked(data, forward=1):                              ###
#   """Focus the next (or previous, with forward=0) window in a stacked ###
#      order."""                                                        ###
# def focus_prev_stacked(data):                                         ###
#   """Focus the previous window in a stacked order."""                 ###
# def focus_next(data, num=1, forward=1):                               ###
#   """Focus the next (or previous, with forward=0) window in a linear  ###
#      order."""                                                        ###
# def focus_prev(data, num=1):                                          ###
#   """Focus the previous window in a linear order."""                  ###
###                                                                     ###
# All of these functions call be used as callbacks for bindings         ###
# directly.                                                             ###
###                                                                     ###
###########################################################################

import otk
import ob

# maintain a list of clients, stacked in focus order
_clients = []
# maintaint he current focused window
_doing_stacked = 0

def _new_win(data):
    global _clients
    global _doing_stacked
    global _cyc_w;

    if _doing_stacked:
        _clients.insert(_clients.index(_cyc_w), data.client.window())
        _create_popup_list(data)
        _hilite_popup_list(data)
    else:
        if not len(_clients):
            _clients.append(data.client.window())
        else:
            _clients.insert(1, data.client.window()) # insert in 2nd slot

def _close_win(data):
    global _clients
    global _cyc_w;
    global _doing_stacked

    if not _doing_stacked:
        # not in the middle of stacked cycling, so who cares
        _clients.remove(data.client.window())
    else:
        # have to fix the cycling if we remove anything
        win = data.client.window()
        if _cyc_w == win:
            _do_stacked_cycle(data, 1) # cycle off the window first, forward
        _clients.remove(win)
        _create_popup_list(data)

def _focused(data):
    global _clients
    global _doing_stacked
    global _cyc_w
    
    if data.client:
        if not _doing_stacked: # only move the window when we're not cycling
            win = data.client.window()
            # move it to the top
            _clients.remove(win)
            _clients.insert(0, win)
        else: # if we are cycling, then update our pointer
            _cyc_w = data.client.window()
            _hilite_popup_list(data)
    elif fallback: 
        # pass around focus
        desktop = ob.openbox.screen(_cyc_screen).desktop()
        for w in _clients:
            client = ob.openbox.findClient(w)
            if client and (client.desktop() == desktop and \
                           client.normal() and client.focus()):
                break
        if _doing_stacked:
            _cyc_w = 0
            _hilite_popup_list(data)

_cyc_mask = 0
_cyc_key = 0
_cyc_w = 0 # last window cycled to
_cyc_screen = 0

def _do_stacked_cycle(data, forward):
    global _cyc_w
    global stacked_cycle_raise
    global _clients

    clients = _clients[:] # make a copy

    if not forward:
        clients.reverse()

    try:
        i = clients.index(_cyc_w) + 1
    except ValueError:
        i = 1
    clients = clients[i:] + clients[:i]
        
    desktop = ob.openbox.screen(data.screen).desktop()
    for w in clients:
        client = ob.openbox.findClient(w)
        if client and (client.desktop() == desktop and \
                       client.normal() and client.focus()):
            if stacked_cycle_raise:
                ob.openbox.screen(data.screen).raiseWindow(client)
            return

def _focus_stacked_ungrab(data):
    global _cyc_mask;
    global _cyc_key;
    global _doing_stacked;

    if data.action == ob.KeyAction.Release:
        # have all the modifiers this started with been released?
        if not _cyc_mask & data.state:
            _destroy_popup_list()
            ob.kungrab()
            ob.mungrab()
            _doing_stacked = 0;
            if cycle_raise:
                client = ob.openbox.findClient(_cyc_w)
                if client:
                    ob.openbox.screen(data.screen).raiseWindow(client)

_list_widget = 0
_list_labels = []
_list_windows = []

def _hilite_popup_list(data):
    global _cyc_w, _doing_stacked
    global _list_widget, _list_labels, _list_windows
    found = 0

    if not _list_widget and _doing_stacked:
        _create_popup_list(data)
    
    if _list_widget:
        i = 0
        for w in _list_windows:
            if w == _cyc_w:
                _list_labels[i].focus()
                found = 1
            else:
                _list_labels[i].unfocus()
            i += 1
    if not found:
        _create_popup_list(data)

def _destroy_popup_list():
    global _list_widget, _list_labels, _list_windows
    if _list_widget:
        _list_windows = []
        _list_labels = []
        _list_widget = 0
    
def _create_popup_list(data):
    global _list_widget, _list_labels, _list_windows, _clients

    if _list_widget:
        _destroy_popup_list()
    
    style = ob.openbox.screen(data.screen).style()
    _list_widget = otk.Widget(ob.openbox, style,
                              otk.Widget.Vertical, 0,
                              style.bevelWidth(), 1)
    t = style.titlebarFocusBackground()
    _list_widget.setTexture(t)

    titles = []
    font = style.labelFont()
    height = font.height()
    longest = 0
    for c in _clients:
        client = ob.openbox.findClient(c)
        desktop = ob.openbox.screen(data.screen).desktop()
        if client and ((client.desktop() == desktop or
                        client.desktop() == 0xffffffff) and \
                       client.normal() and (client.canFocus() or
                                            client.focusNotify())):
            t = client.title()
            if len(t) > 50: # limit the length of titles
                t = t[:24] + "..." + t[-24:]
            titles.append(t)
            _list_windows.append(c)
            l = font.measureString(t)
            if l > longest: longest = l
    if len(titles) > 1:
        for t in titles:
            w = otk.FocusLabel(_list_widget)
            w.fitSize(longest, height)
            w.setText(t)
            w.unfocus()
            _list_labels.append(w)
        _list_widget.update()
        area = otk.display.screenInfo(data.screen).rect()
        _list_widget.move(area.x() + (area.width() -
                                      _list_widget.width()) / 2,
                          area.y() + (area.height() -
                                      _list_widget.height()) / 2)
        _list_widget.show(1)
    else:
        _destroy_popup_list() # nothing (or only 1) to list

def focus_next_stacked(data, forward=1):
    """Focus the next (or previous, with forward=0) window in a stacked
       order."""
    global _cyc_mask
    global _cyc_key
    global _cyc_w
    global _cyc_screen
    global _doing_stacked

    if _doing_stacked:
        if _cyc_key == data.key:
            _do_stacked_cycle(data,forward)
    else:
        _cyc_mask = data.state
        _cyc_key = data.key
        _cyc_w = 0
        _cyc_screen = data.screen
        _doing_stacked = 1

        global stacked_cycle_popup_list
        if stacked_cycle_popup_list:
            _create_popup_list(data)

        ob.kgrab(data.screen, _focus_stacked_ungrab)
        # the pointer grab causes pointer events during the keyboard grab to
        # go away, which means we don't get enter notifies when the popup
        # disappears, screwing up the focus
        ob.mgrab(data.screen)
        focus_next_stacked(data, forward) # start with the first press

def focus_prev_stacked(data):
    """Focus the previous window in a stacked order."""
    focus_next_stacked(data, forward=0)

def focus_next(data, num=1, forward=1):
    """Focus the next (or previous, with forward=0) window in a linear
       order."""
    screen = ob.openbox.screen(data.screen)
    count = screen.clientCount()

    if not count: return # no clients
    
    target = 0
    if data.client:
        client_win = data.client.window()
        found = 0
        r = range(count)
        if not forward:
            r.reverse()
        for i in r:
            if found:
                target = i
                found = 2
                break
            elif screen.client(i).window() == client_win:
                found = 1
        if found == 1: # wraparound
            if forward: target = 0
            else: target = count - 1

    t = target
    curdesk = screen.desktop()
    while 1:
        client = screen.client(t)
        if client.normal() and \
               (client.desktop() == curdesk or client.desktop() == 0xffffffff)\
               and client.focus():
            if cycle_raise:
                screen.raiseWindow(client)
            return
        if forward:
            t += num
            if t >= count: t -= count
        else:
            t -= num
            if t < 0: t += count
        if t == target: return # nothing to focus

def focus_prev(data, num=1):
    """Focus the previous window in a linear order."""
    focus_next(data, num, forward=0)


ob.ebind(ob.EventAction.NewWindow, _new_win)
ob.ebind(ob.EventAction.CloseWindow, _close_win)
ob.ebind(ob.EventAction.Focus, _focused)

print "Loaded focus.py"
