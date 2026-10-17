"""Terminal UI for Arise Cloner: banner, panels, log lines, progress bars,
result screens and the inquirer theme. Nothing here touches Discord."""
import os
import re
import sys
import time

from rich.box import ROUNDED
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, ProgressColumn, SpinnerColumn,
                           TextColumn)
from rich.table import Table
from rich.text import Text

PURPLE = '#9D4EDD'
CYAN = '#00F5FF'
BLUE = '#3A5BFF'
DEEP = '#1B2A6B'
MAGENTA = '#FF2BD6'
RED = '#FF6B81'
YELLOW = '#FFD166'
TEXT = '#D7D9F5'
MUTED = '#7C80A8'

INDENT = 2

# Make sure the box-drawing / block characters survive on Windows consoles.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

console = Console(highlight=False)

# Counters filled by the log helpers, shown on the final summary screen.
STATS = {'ok': 0, 'removed': 0, 'warn': 0, 'err': 0}

_ACTIVE_PROGRESS = []


def _rgb(hex_color: str):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(_rgb(c1), _rgb(c2)))


def gradient_text(line: str, stops=(PURPLE, BLUE, CYAN)) -> Text:
    """Horizontal multi-stop colour gradient for one line of text."""
    out = Text()
    n = len(line)
    segments = len(stops) - 1
    for i, ch in enumerate(line):
        t = i / max(n - 1, 1)
        seg = min(int(t * segments), segments - 1)
        local = t * segments - seg
        r, g, b = _lerp(stops[seg], stops[seg + 1], local)
        out.append(ch, style=f'bold #{r:02x}{g:02x}{b:02x}')
    return out


def cw() -> int:
    """Content width: wide enough to look good, never wider than the window."""
    return max(44, min(console.width - 2 * INDENT, 84))


def show(renderable=''):
    """Print with the standard left margin so everything lines up."""
    console.print(Padding(renderable, (0, 0, 0, INDENT)))


def gap(lines: int = 1):
    for _ in range(lines):
        console.print()


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def divider(color: str = DEEP):
    show(Text('─' * cw(), style=color))


_LETTERS = {
    'A': [' █████╗ ', '██╔══██╗', '███████║', '██╔══██║', '██║  ██║', '╚═╝  ╚═╝'],
    'R': ['██████╗ ', '██╔══██╗', '██████╔╝', '██╔══██╗', '██║  ██║', '╚═╝  ╚═╝'],
    'I': ['██╗', '██║', '██║', '██║', '██║', '╚═╝'],
    'S': ['███████╗', '██╔════╝', '███████╗', '╚════██║', '███████║', '╚══════╝'],
    'E': ['███████╗', '██╔════╝', '█████╗  ', '██╔══╝  ', '███████╗', '╚══════╝'],
}
BANNER_LINES = [''.join(_LETTERS[c][row] for c in 'ARISE') for row in range(6)]


def banner(version: str, python: str, dpy: str, animate: bool = False):
    clear()
    gap()
    for line in BANNER_LINES:
        show(gradient_text(line))
        if animate:
            time.sleep(0.05)
    gap()
    show(Text.assemble(
        ('◆ ', f'bold {MAGENTA}'),
        ('SERVER CLONER', f'bold {CYAN}'),
        ('   v' + version, f'bold {PURPLE}'),
        ('   ·   ', MUTED),
        (f'Python {python}', MUTED),
        ('   ·   ', MUTED),
        (f'discord.py {dpy}', MUTED),
    ))
    divider()
    gap()


STEP_NAMES = ['Mode', 'Credentials', 'Review', 'Clone']


def steps(current: int):
    """Breadcrumb: finished steps in cyan, current in magenta, next muted."""
    line = Text()
    for i, name in enumerate(STEP_NAMES):
        if i:
            line.append('  ──  ', style=DEEP)
        if i < current:
            line.append(f'✔ {name}', style=CYAN)
        elif i == current:
            line.append(f'● {name}', style=f'bold {MAGENTA}')
        else:
            line.append(f'○ {name}', style=MUTED)
    show(line)
    gap()


def section(title: str, subtitle: str = ''):
    line = Text()
    line.append('▌ ', style=f'bold {MAGENTA}')
    line.append(title.upper(), style=f'bold {CYAN}')
    if subtitle:
        line.append(f'   {subtitle}', style=MUTED)
    show(line)
    divider()


def panel(body, title: str = None, border: str = PURPLE, width: int = None,
          padding=(0, 2)) -> Panel:
    return Panel(
        body,
        title=Text(f' {title} ', style=f'bold {CYAN}') if title else None,
        title_align='left',
        border_style=border,
        box=ROUNDED,
        padding=padding,
        width=width or cw(),
    )


def kv_table(rows, key_color: str = PURPLE) -> Table:
    """Aligned 'Label   value' rows. Values may be str or rich Text."""
    grid = Table.grid(padding=(0, 3))
    grid.add_column(style=f'bold {key_color}', no_wrap=True)
    grid.add_column()
    for key, value in rows:
        if not isinstance(value, Text):
            value = Text(str(value), style=TEXT)
        grid.add_row(key, value)
    return grid


def pair(left, right):
    """Two panels side by side on wide terminals, stacked on narrow ones.
    left / right are (body, title) tuples."""
    if cw() >= 76:
        half = (cw() - 1) // 2
        grid = Table.grid(padding=(0, 1))
        grid.add_column()
        grid.add_column()
        grid.add_row(panel(left[0], left[1], width=half),
                     panel(right[0], right[1], border=BLUE, width=half))
        show(grid)
    else:
        show(panel(left[0], left[1]))
        show(panel(right[0], right[1], border=BLUE))


_NOTICE = {
    'danger': (RED, '✖'),
    'warning': (YELLOW, '▲'),
    'info': (CYAN, '●'),
}


def notice(kind: str, label: str, message: str):
    color, icon = _NOTICE[kind]
    body = Text.assemble((f'{icon} {label}  ', f'bold {color}'),
                         (message, TEXT))
    show(panel(body, border=color))


# Log lines, used by cloner.py through its print_* wrappers
_ANSI = re.compile(r'(\x1b\[[0-9;]*m)')
_RESET_CODES = {'0', '22', '31', '32', '34', '35', '36', '37', '39'}


def _format(message, base: str, highlight: str) -> Text:
    """Turn a message that may contain raw colorama codes into themed Text.
    The yellow colorama code marks 'the name of the thing', which we render
    as a highlight; every other code is dropped."""
    out = Text()
    marked = False
    for part in _ANSI.split(str(message)):
        if not part:
            continue
        if _ANSI.fullmatch(part):
            code = part[2:-1]
            if code == '33':
                marked = True
            elif code in _RESET_CODES:
                marked = False
            continue
        part = part.replace('\n', '\n' + ' ' * 5)
        out.append(part, style=f'bold {highlight}' if marked else base)
    return out


def _log(icon: str, color: str, message, stat: str, base: str = TEXT,
         highlight: str = CYAN):
    STATS[stat] += 1
    line = Text.assemble(('  ', ''), (icon, f'bold {color}'), ('  ', ''))
    line.append_text(_format(message, base, highlight))
    console.print(Padding(line, (0, 0, 0, INDENT - 2)))


def ok(message):
    _log('✔', CYAN, message, 'ok')


def removed(message):
    _log('✕', MAGENTA, message, 'removed')


def warn(message):
    _log('▲', YELLOW, message, 'warn', base=YELLOW, highlight='#FFFFFF')


def err(message):
    _log('✖', RED, message, 'err', base=RED, highlight='#FFFFFF')


def info(message):
    console.print(Padding(
        Text.assemble(('  ● ', f'bold {PURPLE}'), (str(message), TEXT)),
        (0, 0, 0, INDENT - 2)))


def reset_stats():
    for key in STATS:
        STATS[key] = 0


class _Elapsed(ProgressColumn):
    def render(self, task):
        seconds = task.finished_time if task.finished else task.elapsed
        seconds = int(seconds or 0)
        return Text(f'{seconds // 60:02d}:{seconds % 60:02d}', style=MUTED)


def _progress(transient: bool = False) -> Progress:
    return Progress(
        TextColumn('  '),
        SpinnerColumn('dots', style=CYAN, finished_text=Text('✔', style=CYAN)),
        TextColumn('{task.description:<24}', style=f'bold {TEXT}'),
        BarColumn(bar_width=32, style=DEEP, complete_style=PURPLE,
                  finished_style=CYAN, pulse_style=MAGENTA),
        TextColumn('{task.percentage:>3.0f}%', style=f'bold {CYAN}'),
        TextColumn('{task.completed:.0f}/{task.total:.0f}', style=MUTED),
        _Elapsed(),
        console=console,
        transient=transient,
        refresh_per_second=20,
    )


def track(items, label: str):
    """Drop-in replacement for iterating a list: shows a live progress bar
    that advances after each item has been fully processed. Log lines printed
    meanwhile appear above the bar."""
    items = list(items)
    if not items:
        return
    progress = _progress()
    task = progress.add_task(label, total=len(items))
    _ACTIVE_PROGRESS.append(progress)
    progress.start()
    try:
        for item in items:
            yield item
            progress.advance(task)
    finally:
        progress.stop()
        if progress in _ACTIVE_PROGRESS:
            _ACTIVE_PROGRESS.remove(progress)


def halt():
    """Stop any progress bar still on screen (used when an error aborts a step)."""
    for progress in list(_ACTIVE_PROGRESS):
        progress.stop()
        _ACTIVE_PROGRESS.remove(progress)


def loading(label: str, seconds: float = 1.0, ticks: int = 40):
    """Short animated bar for transitions."""
    with _progress(transient=True) as progress:
        task = progress.add_task(label, total=ticks)
        for _ in range(ticks):
            time.sleep(seconds / ticks)
            progress.advance(task)


def connecting(label: str = 'Connecting to Discord'):
    """Spinner shown until the client is ready. Call .start() / .stop()."""
    return console.status(Text(f' {label}…', style=f'bold {CYAN}'),
                          spinner='dots', spinner_style=PURPLE)


def logged_in(user):
    body = Text.assemble(('✔ ', f'bold {CYAN}'), ('Logged in as ', TEXT),
                         (str(user), f'bold {CYAN}'))
    gap()
    show(panel(body, border=CYAN, width=min(cw(), 52)))
    gap()


def finish(mode_name: str, parts: list, took: str, runs: int):
    """Success (or 'finished with issues') summary after a clone."""
    errors, warnings = STATS['err'], STATS['warn']
    if errors:
        color, icon, title = YELLOW, '▲', 'COMPLETED WITH ISSUES'
        headline = 'Some items could not be processed. Check the log above.'
    else:
        color, icon, title = CYAN, '✔', 'CLONE COMPLETE'
        headline = 'All selected components were processed successfully.'

    rows = [
        ('Mode', mode_name),
        ('Cloned', ', '.join(parts) if parts else '-'),
        ('Duration', Text(took, style=f'bold {CYAN}')),
        ('Actions', str(STATS['ok'] + STATS['removed'])),
        ('Warnings', Text(str(warnings),
                          style=f'bold {YELLOW}' if warnings else MUTED)),
        ('Errors', Text(str(errors),
                        style=f'bold {RED}' if errors else MUTED)),
        ('Total clones', str(runs)),
    ]
    body = Group(
        Text.assemble((f'{icon} ', f'bold {color}'), (headline, f'bold {TEXT}')),
        Text(''),
        kv_table(rows),
    )
    gap()
    show(panel(body, title, border=color, padding=(1, 2)))
    gap()


def credits(version: str):
    title = Text.assemble(('◆ ', f'bold {MAGENTA}'),
                          ('ARISE CLONER', f'bold {CYAN}'),
                          (f'  v{version}', f'bold {PURPLE}'))
    rows = [
        ('Author:', 'difftheog  (@difftheog on Discord)'),
        ('Source:', Text('https://github.com/difftheog/Arise-Cloner', style=CYAN)),
        ('Support:', 'Open an issue on GitHub or DM the author'),
    ]
    body = Group(
        title,
        Text(''),
        kv_table(rows),
        Text(''),
        Text('★ If Arise Cloner saved you time, star the repository.',
             style=f'italic {MAGENTA}'),
    )
    gap()
    show(panel(body, 'CREDITS', padding=(1, 2)))
    show(Text('Thanks for using Arise Cloner. See you next time.', style=MUTED))
    gap()


def inquirer_theme():
    """Cyan / purple / magenta theme for the inquirer menus.
    Returns None if the installed inquirer version can't be themed, in which
    case the default theme is used."""
    try:
        from blessed import Terminal
        from inquirer.themes import Default

        term = Terminal()

        def color(hex_color):
            return term.color_rgb(*_rgb(hex_color))

        class AriseTheme(Default):
            def __init__(self):
                super().__init__()
                self.Question.mark_color = color(MAGENTA)
                self.Question.brackets_color = color(PURPLE)
                self.Question.default_color = color(MUTED)
                self.Checkbox.selection_color = color(CYAN)
                self.Checkbox.selection_icon = '❯'
                self.Checkbox.selected_icon = '◉'
                self.Checkbox.selected_color = color(CYAN)
                self.Checkbox.unselected_icon = '○'
                self.Checkbox.unselected_color = color(TEXT)
                self.List.selection_color = color(CYAN)
                self.List.selection_cursor = '❯'
                self.List.unselected_color = color(TEXT)

        return AriseTheme()
    except Exception:
        return None