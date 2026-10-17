"""Mouse wheel support for the inquirer menus.

On Windows the console is put into mouse-input mode while a prompt is on
screen and wheel notches are turned into Up/Down key presses, so scrolling
works in Windows Terminal and the classic console. Everything else about the
prompts (keyboard, typing, Ctrl+C) behaves as before. On other platforms the
normal keyboard reader is used.
"""
import contextlib
import ctypes
import os
from ctypes import wintypes

import readchar
from readchar import key

from inquirer.events import KeyEventGenerator
from inquirer.render.console import ConsoleRender

STD_INPUT_HANDLE = -10

ENABLE_PROCESSED_INPUT = 0x0001
ENABLE_LINE_INPUT = 0x0002
ENABLE_ECHO_INPUT = 0x0004
ENABLE_MOUSE_INPUT = 0x0010
ENABLE_QUICK_EDIT_MODE = 0x0040
ENABLE_EXTENDED_FLAGS = 0x0080

KEY_EVENT = 0x0001
MOUSE_EVENT = 0x0002
MOUSE_WHEELED = 0x0004

# virtual-key code -> the key constant inquirer understands
VK_KEYS = {
    0x26: key.UP,
    0x28: key.DOWN,
    0x25: key.LEFT,
    0x27: key.RIGHT,
    0x24: key.HOME,
    0x23: key.END,
    0x21: key.PAGE_UP,
    0x22: key.PAGE_DOWN,
    0x2D: key.INSERT,
    0x2E: key.DELETE,
}


class KeyEventRecord(ctypes.Structure):
    _fields_ = [
        ('key_down', wintypes.BOOL),
        ('repeat', wintypes.WORD),
        ('vk', wintypes.WORD),
        ('scan', wintypes.WORD),
        ('char', wintypes.WCHAR),
        ('state', wintypes.DWORD),
    ]


class MouseEventRecord(ctypes.Structure):
    _fields_ = [
        ('x', wintypes.SHORT),
        ('y', wintypes.SHORT),
        ('buttons', wintypes.DWORD),
        ('state', wintypes.DWORD),
        ('flags', wintypes.DWORD),
    ]


class EventUnion(ctypes.Union):
    _fields_ = [('key', KeyEventRecord), ('mouse', MouseEventRecord)]


class InputRecord(ctypes.Structure):
    _fields_ = [('type', wintypes.WORD), ('event', EventUnion)]


_state = {'handle': None}


def wheel_key(buttons: int):
    """Up/Down key for a wheel event, based on the signed delta stored in the
    high word of the button state (positive = wheel rolled away from you)."""
    delta = ctypes.c_short(buttons >> 16).value
    if delta == 0:
        return None
    return key.UP if delta > 0 else key.DOWN


def keypress(vk: int, char: str):
    """Key string for a key-down event, or None for keys that only modify
    (Shift, Ctrl, Alt on their own)."""
    if vk in VK_KEYS:
        return VK_KEYS[vk]
    if char and char != '\x00':
        return char
    return None


def _read_record(handle) -> InputRecord:
    record = InputRecord()
    count = wintypes.DWORD()
    ok = ctypes.windll.kernel32.ReadConsoleInputW(
        handle, ctypes.byref(record), 1, ctypes.byref(count))
    if not ok or count.value == 0:
        raise OSError('could not read console input')
    return record


def _next_key(handle) -> str:
    while True:
        record = _read_record(handle)
        if record.type == MOUSE_EVENT:
            mouse = record.event.mouse
            if mouse.flags & MOUSE_WHEELED:
                pressed = wheel_key(mouse.buttons)
                if pressed:
                    return pressed
        elif record.type == KEY_EVENT and record.event.key.key_down:
            pressed = keypress(record.event.key.vk, record.event.key.char)
            if pressed:
                return pressed


def readkey() -> str:
    """Drop-in for readchar.readkey that also understands the mouse wheel."""
    handle = _state['handle']
    if handle is None:
        return readchar.readkey()

    pressed = _next_key(handle)
    if pressed in readchar.config.INTERRUPT_KEYS:
        raise KeyboardInterrupt

    # characters outside the BMP arrive as two UTF-16 halves
    if '\ud800' <= pressed <= '\udbff':
        pressed += _next_key(handle)
        pressed = pressed.encode('utf-16', errors='surrogatepass').decode('utf-16')
    return pressed


@contextlib.contextmanager
def capture():
    """Turn on mouse input for the console while a prompt is running."""
    if os.name != 'nt':
        yield
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
    old_mode = wintypes.DWORD()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(old_mode)):
        yield  # input isn't a console (redirected), keep the normal reader
        return

    # Same raw mode msvcrt.getwch uses, plus mouse events. Quick-edit has to be
    # off or the console keeps the mouse for text selection.
    mode = old_mode.value
    mode &= ~(ENABLE_PROCESSED_INPUT | ENABLE_LINE_INPUT |
              ENABLE_ECHO_INPUT | ENABLE_QUICK_EDIT_MODE)
    mode |= ENABLE_MOUSE_INPUT | ENABLE_EXTENDED_FLAGS
    if not kernel32.SetConsoleMode(handle, mode):
        yield
        return

    _state['handle'] = handle
    try:
        yield
    finally:
        _state['handle'] = None
        kernel32.SetConsoleMode(handle, old_mode.value)


def make_render(theme=None) -> ConsoleRender:
    return ConsoleRender(event_generator=KeyEventGenerator(readkey),
                         theme=theme)
