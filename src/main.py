import os
import sys
import json
import time

import discord
import inquirer
from rich.table import Table
from rich.text import Text

import ui
import wheel
from cloner import Clone

VERSION = '2.0'
SAVES_FILE = 'saves.json'
PYTHON_VERSION = sys.version.split()[0]

# What can be cloned. Each preset is just a set of these switches.
# Cloning "roles" or "channels" always deletes the old ones in the destination
# first, so the result matches the source.
COMPONENTS = {
    'info': 'Server name & icon',
    'roles': 'Roles (deletes old roles, skips bot roles)',
    'channels': 'Categories & channels (deletes old channels, copies permissions)',
    'emojis': 'Emojis',
    'stickers': 'Stickers',
}

PRESETS = {
    'full': ('Full server', set(COMPONENTS)),
    'roles': ('Only roles', {'roles'}),
    'media': ('Only emojis and stickers', {'emojis', 'stickers'}),
}

_splash_done = False


def load_saves() -> dict:
    try:
        with open(SAVES_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault('server_cloned_successfully', 0)
    return data


def save_saves(data: dict):
    with open(SAVES_FILE, 'w') as f:
        json.dump(data, f)


def banner(animate: bool = False):
    ui.banner(VERSION, PYTHON_VERSION, discord.__version__, animate=animate)


def mask_token(tok: str) -> str:
    tok = tok.strip()
    if len(tok) <= 8:
        return '*' * len(tok)
    return tok[:4] + '*' * (len(tok) - 8) + tok[-4:]


def ask(questions):
    """inquirer.prompt with mouse wheel support that exits cleanly on Ctrl+C."""
    theme = ui.inquirer_theme()
    render = wheel.make_render(theme)
    with wheel.capture():
        answers = inquirer.prompt(questions, render=render,
                                  theme=theme or inquirer.themes.Default())
    if answers is None:
        sys.exit(0)
    return answers


def short(label: str) -> str:
    return label.split(' (')[0]


def home_panels(runs: int):
    """Two info panels above the main menu: what each mode does + session info."""
    modes = ui.kv_table([
        ('Full server', Text('everything below', style=ui.MUTED)),
        ('Roles only', Text('wipe & recreate roles', style=ui.MUTED)),
        ('Media only', Text('emojis & stickers', style=ui.MUTED)),
        ('Custom', Text('pick components', style=ui.MUTED)),
        ('Exit', Text('close Arise', style=ui.MUTED)),
    ], key_color=ui.CYAN)

    session = ui.kv_table([
        ('Version', f'v{VERSION}'),
        ('Python', PYTHON_VERSION),
        ('discord.py', discord.__version__),
        ('Clones done', Text(str(runs), style=f'bold {ui.CYAN}')),
        ('Status', Text('● Ready', style=f'bold {ui.CYAN}')),
    ])
    ui.pair((modes, 'MODES'), (session, 'SESSION'))
    ui.gap()


def main_menu(runs: int = 0):
    """Returns the set of components to clone, or exits."""
    global _splash_done
    banner(animate=not _splash_done)
    _splash_done = True
    ui.steps(0)
    home_panels(runs)

    choice = ask([
        inquirer.List(
            'choice',
            message='Main menu',
            choices=[
                ('Clone full server', 'full'),
                ('Clone only roles', 'roles'),
                ('Clone only emojis and stickers', 'media'),
                ('Custom (pick exactly what to clone)', 'custom'),
                ('Exit', 'exit'),
            ],
        )
    ])['choice']

    if choice == 'exit':
        sys.exit(0)
    if choice != 'custom':
        name, parts = PRESETS[choice]
        return name, set(parts)

    while True:
        picked = ask([
            inquirer.Checkbox(
                'parts',
                message='Select what to clone (space = toggle, enter = confirm)',
                choices=[(label, key) for key, label in COMPONENTS.items()],
            )
        ])['parts']
        if picked:
            return 'Custom', set(picked)
        ui.err('Select at least one option.')


def credentials_menu():
    banner()
    ui.steps(1)
    ui.section('Credentials', 'your token is hidden while typing')
    ui.gap()
    numeric = lambda _, x: x.strip().isdigit() and len(x.strip()) >= 3
    answers = ask([
        inquirer.Password('token', message='Your token'),
        inquirer.Text('source',
                      message='ID of the server to copy FROM',
                      validate=numeric),
        inquirer.Text('dest',
                      message='ID of the server to paste INTO',
                      validate=numeric),
    ])
    token = answers['token'].strip()
    source, dest = answers['source'].strip(), answers['dest'].strip()
    if not token:
        ui.err('Token cannot be empty.')
        time.sleep(1.5)
        return credentials_menu()
    if source == dest:
        ui.err('Source and destination are the same server. '
               'That would wipe it. Pick two different servers.')
        time.sleep(2.5)
        return credentials_menu()
    return token, source, dest


def confirm_screen(mode_name, parts, token, source, dest) -> bool:
    banner()
    ui.steps(2)

    overview = ui.kv_table([
        ('Mode', Text(mode_name, style=f'bold {ui.CYAN}')),
        ('Token', mask_token(token)),
        ('Copy from', source),
        ('Paste into', dest),
    ])
    ui.show(ui.panel(overview, 'REVIEW'))

    plan = Table(box=None, show_header=True, pad_edge=False,
                 header_style=f'bold {ui.MAGENTA}', padding=(0, 4, 0, 0))
    plan.add_column('PART', style=ui.TEXT, no_wrap=True)
    plan.add_column('ACTION', no_wrap=True)
    for key, label in COMPONENTS.items():
        if key in parts:
            if key in ('roles', 'channels'):
                action = Text('Delete old, then clone', style=ui.RED)
            else:
                action = Text('Clone', style=ui.CYAN)
        else:
            action = Text('Skipped', style=ui.MUTED)
        plan.add_row(short(label), action)
    ui.show(ui.panel(plan, 'WHAT WILL HAPPEN', border=ui.BLUE))

    deleting = [k for k in ('roles', 'channels') if k in parts]
    if deleting:
        ui.notice('danger', 'WARNING',
                  f"All existing {' and '.join(deleting)} in the destination "
                  f"server will be deleted.")
    ui.notice('warning', 'NOTICE',
              "Logging in with a user token breaks Discord's Terms of "
              "Service and can get the account banned.")
    ui.gap()
    return ask([inquirer.Confirm('ok', message='Start?',
                                 default=False)])['ok']


async def run_clone(client, parts, source_id, dest_id, saves):
    guild_from = client.get_guild(int(source_id))
    guild_to = client.get_guild(int(dest_id))
    if guild_from is None:
        ui.err(f'You are not a member of the source server ({source_id}).')
        return False
    if guild_to is None:
        ui.err(f'You are not a member of the destination server ({dest_id}).')
        return False

    # Order matters: info -> wipe channels -> wipe roles -> roles -> channels -> media
    if 'info' in parts:
        await Clone.guild_edit(guild_to, guild_from)
    if 'channels' in parts:
        await Clone.channels_delete(guild_to)
    if 'roles' in parts:
        await Clone.roles_delete(guild_to)
        await Clone.roles_create(guild_to, guild_from)
    elif 'channels' in parts:
        Clone.map_existing_roles(guild_to, guild_from)
    if 'channels' in parts:
        await Clone.categories_create(guild_to, guild_from)
        await Clone.channels_create(guild_to, guild_from)
    if 'emojis' in parts:
        ui.info('Cloning emojis. This may take a few moments.')
        await Clone.emojis_create(guild_to, guild_from)
    if 'stickers' in parts:
        ui.info('Cloning stickers. This may take a few moments.')
        await Clone.stickers_create(guild_to, guild_from)

    saves['server_cloned_successfully'] += 1
    save_saves(saves)
    return True


def start_session(token, parts, source_id, dest_id, saves,
                  mode_name='Custom') -> bool:
    """Logs in, clones, logs out. Returns False if the login failed."""
    client = discord.Client()
    state = {'login_ok': True}
    status = ui.connecting()

    @client.event
    async def on_ready():
        status.stop()
        started = time.time()
        ui.reset_stats()
        ui.logged_in(client.user)
        try:
            ok = await run_clone(client, parts, source_id, dest_id, saves)
            if ok:
                took = time.strftime('%M:%S', time.gmtime(time.time() - started))
                labels = [short(label) for key, label in COMPONENTS.items()
                          if key in parts]
                ui.finish(mode_name, labels, took,
                          saves['server_cloned_successfully'])
        except discord.Forbidden:
            ui.halt()
            ui.err('Could not clone due to insufficient permissions.')
        except discord.NotFound:
            ui.halt()
            ui.err('Could not find one of the elements to copy.')
        except discord.HTTPException as e:
            ui.halt()
            ui.err(f'Discord API error: {e}')
        except Exception as e:
            ui.halt()
            ui.err(f'An error occurred: {e}')
        finally:
            ui.halt()
            ui.info(f'Ending session on {client.user}')
            await client.close()

    status.start()
    try:
        # log_handler=None keeps discord's own logging out of the terminal UI
        client.run(token, log_handler=None)
    except discord.LoginFailure:
        state['login_ok'] = False
        status.stop()
        ui.err('The token is invalid.')
    finally:
        status.stop()
    return state['login_ok']


def main():
    saves = load_saves()
    try:
        while True:
            mode_name, parts = main_menu(saves['server_cloned_successfully'])
            token, source_id, dest_id = credentials_menu()
            if not confirm_screen(mode_name, parts, token, source_id, dest_id):
                continue  # back to the main menu

            banner()
            ui.steps(3)
            ui.loading('Preparing session', 0.9)
            ui.section('Cloning in progress')
            if start_session(token, parts, source_id, dest_id, saves,
                             mode_name):
                break
            again = ask([inquirer.Confirm('retry', message='Try again?',
                                          default=True)])['retry']
            if not again:
                break
    except (KeyboardInterrupt, SystemExit):
        ui.halt()
        ui.credits(VERSION)
        return

    ui.credits(VERSION)
    ui.show(Text('Press Enter to exit...', style=ui.MUTED))
    input()


if __name__ == '__main__':
    main()