import asyncio
import io
import random

import discord
from colorama import Fore

import ui

# Source object ID -> the object created for it in the destination server.
# Lets permissions and categories line up by ID instead of by name, since
# names can be duplicated.
ROLE_MAP = {}
CATEGORY_MAP = {}


def convert_overwrites(guild_to: discord.Guild, overwrites: dict) -> dict:
    """Translate permission overwrites from the source guild to the destination.

    @everyone maps to the destination @everyone and cloned roles map to their
    new copies. Bot/managed roles and individual members are skipped because
    they don't exist in the destination server.
    """
    result = {}
    for target, overwrite in overwrites.items():
        if isinstance(target, discord.Role):
            if target.is_default():
                result[guild_to.default_role] = overwrite
            elif target.id in ROLE_MAP:
                result[ROLE_MAP[target.id]] = overwrite
    return result


class Clone:
    @staticmethod
    def map_existing_roles(guild_to: discord.Guild, guild_from: discord.Guild):
        """For cloning channels without roles: match source roles to roles
        that already exist in the destination, by name."""
        ROLE_MAP.clear()
        ROLE_MAP[guild_from.default_role.id] = guild_to.default_role
        by_name = {r.name: r for r in guild_to.roles if not r.is_default()}
        matched = 0
        for role in guild_from.roles:
            if role.is_default() or role.managed:
                continue
            if role.name in by_name:
                ROLE_MAP[role.id] = by_name[role.name]
                matched += 1
        print_warning(
            f"Roles not cloned: {matched} source role(s) matched by name in the destination for channel permissions."
        )

    @staticmethod
    async def roles_delete(guild_to: discord.Guild):
        for role in ui.track(guild_to.roles, "Deleting roles"):
            try:
                if not role.is_default() and not role.managed:
                    await role.delete()
                    print_delete(
                        f"The role {Fore.YELLOW}{role.name}{Fore.BLUE} has been deleted"
                    )
                    await asyncio.sleep(random.uniform(0.10, 0.15))
            except discord.Forbidden:
                print_error(
                    f"Error deleting the role: {Fore.YELLOW}{role.name}{Fore.RED} Insufficient permissions.{Fore.RESET}"
                )
            except discord.HTTPException as e:
                print_warning(f"Could not delete role {role.name}: {e}")

    @staticmethod
    async def roles_create(guild_to: discord.Guild, guild_from: discord.Guild):
        ROLE_MAP.clear()

        # Copy @everyone permissions first so channel overwrites behave the same
        try:
            await guild_to.default_role.edit(
                permissions=guild_from.default_role.permissions)
            ROLE_MAP[guild_from.default_role.id] = guild_to.default_role
        except discord.HTTPException:
            print_warning("Could not copy the @everyone permissions.")

        roles = []
        for role in guild_from.roles:
            if role.is_default():
                continue
            # Managed roles belong to bots, integrations or boosting and can't
            # be created by hand.
            if role.managed:
                print_warning(f"Skipping bot/managed role: {role.name}")
                continue
            roles.append(role)
        roles = roles[::-1]  # lowest first, so the hierarchy comes out right

        for role in ui.track(roles, "Creating roles"):
            try:
                new_role = await guild_to.create_role(
                    name=role.name,
                    permissions=role.permissions,
                    colour=role.colour,
                    hoist=role.hoist,
                    mentionable=role.mentionable)
                ROLE_MAP[role.id] = new_role
                print_add(
                    f"The role {Fore.YELLOW}{role.name}{Fore.BLUE} has been created"
                )
                await asyncio.sleep(random.uniform(0.3, 0.6))
            except discord.Forbidden:
                print_error(
                    f"Error creating the role: {Fore.YELLOW}{role.name}{Fore.RED} Insufficient permissions.{Fore.RESET}"
                )
                await asyncio.sleep(random.uniform(0.2, 0.4))
            except discord.HTTPException as e:
                print_warning(f"Could not create role {role.name}: {e}")
                await asyncio.sleep(2)

    @staticmethod
    async def channels_delete(guild_to: discord.Guild):
        for channel in ui.track(guild_to.channels, "Deleting channels"):
            try:
                await channel.delete()
                print_delete(
                    f"The channel {Fore.YELLOW}{channel.name}{Fore.BLUE} has been deleted"
                )
                await asyncio.sleep(0.20)
            except discord.Forbidden:
                print_error(
                    f"Error deleting the channel: {Fore.YELLOW}{channel.name}{Fore.RED} Insufficient permissions.{Fore.RESET}"
                )
                await asyncio.sleep(random.randint(2, 3))
            except discord.HTTPException as e:
                print_warning(f"Could not delete {channel.name}: {e}")
                await asyncio.sleep(2)

    @staticmethod
    async def categories_create(guild_to: discord.Guild,
                                guild_from: discord.Guild):
        CATEGORY_MAP.clear()
        for category in ui.track(guild_from.categories, "Creating categories"):
            try:
                new_category = await guild_to.create_category(
                    name=category.name,
                    overwrites=convert_overwrites(guild_to,
                                                  category.overwrites))
                await new_category.edit(position=category.position)
                CATEGORY_MAP[category.id] = new_category
                print_add(
                    f"The category {Fore.YELLOW}{category.name}{Fore.BLUE} has been created"
                )
                await asyncio.sleep(random.uniform(1, 2))
            except discord.Forbidden:
                print_error(
                    f"Error creating the category: {Fore.YELLOW}{category.name}{Fore.RED} Insufficient permissions.{Fore.RESET}"
                )
                await asyncio.sleep(random.randint(2, 3))
            except discord.HTTPException as e:
                print_warning(f"Could not create category {category.name}: {e}")
                await asyncio.sleep(2)

    @staticmethod
    async def channels_create(guild_to: discord.Guild,
                              guild_from: discord.Guild):
        for channel in ui.track(guild_from.text_channels, "Creating text channels"):
            try:
                category = CATEGORY_MAP.get(
                    channel.category.id) if channel.category else None
                overwrites = convert_overwrites(guild_to, channel.overwrites)
                try:
                    await guild_to.create_text_channel(
                        name=channel.name,
                        overwrites=overwrites,
                        category=category,
                        position=channel.position,
                        topic=channel.topic,
                        slowmode_delay=channel.slowmode_delay,
                        nsfw=channel.nsfw)
                except discord.HTTPException:
                    # Retry with just the basics (a long topic, for instance)
                    await guild_to.create_text_channel(name=channel.name,
                                                       overwrites=overwrites,
                                                       category=category)
                print_add(
                    f"The text channel {Fore.YELLOW}{channel.name}{Fore.BLUE} has been created"
                )
                await asyncio.sleep(0.59)
            except discord.Forbidden:
                print_error(f"Error creating text channel: {channel.name}")
                await asyncio.sleep(random.randint(2, 3))
            except discord.HTTPException as e:
                print_error(
                    f"Error creating text channel {channel.name}: {e}")
                await asyncio.sleep(2)

        for channel in ui.track(guild_from.voice_channels, "Creating voice channels"):
            try:
                category = CATEGORY_MAP.get(
                    channel.category.id) if channel.category else None
                overwrites = convert_overwrites(guild_to, channel.overwrites)
                try:
                    await guild_to.create_voice_channel(
                        name=channel.name,
                        overwrites=overwrites,
                        category=category,
                        position=channel.position,
                        bitrate=min(channel.bitrate, guild_to.bitrate_limit),
                        user_limit=channel.user_limit)
                except discord.HTTPException:
                    await guild_to.create_voice_channel(name=channel.name,
                                                        overwrites=overwrites,
                                                        category=category)
                print_add(
                    f"The voice channel {Fore.YELLOW}{channel.name}{Fore.BLUE} has been created"
                )
                await asyncio.sleep(0.48)
            except discord.Forbidden:
                print_error(f"Error creating the voice channel: {channel.name}")
                await asyncio.sleep(random.randint(2, 3))
            except discord.HTTPException as e:
                print_error(
                    f"Error creating voice channel {channel.name}: {e}")
                await asyncio.sleep(2)

    @staticmethod
    async def emojis_create(guild_to: discord.Guild,
                            guild_from: discord.Guild):
        emojis = guild_from.emojis
        if not emojis:
            print_warning("No emoji found.")
            return

        # How many slots the destination has left
        limit = guild_to.emoji_limit
        static_slots = limit - sum(1 for e in guild_to.emojis if not e.animated)
        animated_slots = limit - sum(1 for e in guild_to.emojis if e.animated)
        static_needed = sum(1 for e in emojis if not e.animated)
        animated_needed = sum(1 for e in emojis if e.animated)

        if static_needed > static_slots or animated_needed > animated_slots:
            print_warning(
                f"Not enough emoji slots in the destination server "
                f"(limit {limit} static + {limit} animated, boost level {guild_to.premium_tier}).\n"
                f"   Static:   {max(static_slots, 0)} free, {static_needed} needed\n"
                f"   Animated: {max(animated_slots, 0)} free, {animated_needed} needed\n"
                f"   Only the emojis that fit will be cloned. Boost the server or delete some emojis to fit more."
            )
        else:
            print_add(
                f"Emoji slots OK: {static_needed} static / {animated_needed} animated to clone."
            )

        created = 0
        skipped_no_slot = 0
        for emoji in ui.track(emojis, "Cloning emojis"):
            if emoji.animated and animated_slots <= 0:
                skipped_no_slot += 1
                continue
            if not emoji.animated and static_slots <= 0:
                skipped_no_slot += 1
                continue
            try:
                emoji_image = await emoji.read()
                await guild_to.create_custom_emoji(name=emoji.name,
                                                   image=emoji_image)
                if emoji.animated:
                    animated_slots -= 1
                else:
                    static_slots -= 1
                created += 1
                print_add(
                    f"The emoji {Fore.YELLOW}{emoji.name}{Fore.BLUE} has been created."
                )
                await asyncio.sleep(1)
            except discord.Forbidden:
                print_error(
                    f"Error creating the emoji: {Fore.YELLOW}{emoji.name}{Fore.RED} Insufficient permissions.{Fore.RESET}"
                )
                await asyncio.sleep(random.uniform(2, 3))
            except discord.HTTPException as e:
                # 30008 = maximum number of emojis reached
                if getattr(e, 'code', None) == 30008:
                    if emoji.animated:
                        animated_slots = 0
                    else:
                        static_slots = 0
                    skipped_no_slot += 1
                    print_warning(
                        f"Destination ran out of {'animated' if emoji.animated else 'static'} emoji slots at {emoji.name}."
                    )
                else:
                    print_warning(f"Could not create emoji {emoji.name}: {e}")
                await asyncio.sleep(2)
            except Exception as e:
                print_error(f"Unexpected error with emoji {emoji.name}: {e}")
                await asyncio.sleep(0.47)

        summary = f"Emojis: {created} cloned"
        if skipped_no_slot:
            summary += f", {skipped_no_slot} skipped because the destination has no free slots"
        (print_warning if skipped_no_slot else print_add)(summary)

    @staticmethod
    async def stickers_create(guild_to: discord.Guild,
                              guild_from: discord.Guild):
        """Clone custom stickers (PNG, APNG and GIF; Lottie can't be copied)."""
        try:
            stickers = await guild_from.fetch_stickers()
        except discord.HTTPException as e:
            print_error(f"Could not fetch stickers: {e}")
            return

        if not stickers:
            print_warning("No stickers found.")
            return

        sticker_limit = guild_to.sticker_limit
        try:
            existing = await guild_to.fetch_stickers()
            free_slots = sticker_limit - len(existing)
        except discord.HTTPException:
            free_slots = sticker_limit  # couldn't check, just try

        extensions = {
            discord.StickerFormatType.png: 'png',
            discord.StickerFormatType.apng: 'png',
            discord.StickerFormatType.gif: 'gif',
        }

        cloneable = [s for s in stickers if s.format in extensions]
        if len(cloneable) > free_slots:
            print_warning(
                f"Not enough sticker slots in the destination server "
                f"(limit {sticker_limit}, boost level {guild_to.premium_tier}).\n"
                f"   {max(free_slots, 0)} free, {len(cloneable)} needed\n"
                f"   Only the first {max(free_slots, 0)} sticker(s) will be cloned. "
                f"Boost the server or delete some stickers to fit more."
            )
        else:
            print_add(f"Sticker slots OK: {len(cloneable)} to clone.")

        created = 0
        skipped_no_slot = 0

        for sticker in ui.track(stickers, "Cloning stickers"):
            name = sticker.name
            ext = extensions.get(sticker.format)
            if ext is None:
                print_warning(
                    f"Skipping sticker {name} (Lottie stickers can't be cloned)"
                )
                continue
            if free_slots <= 0:
                skipped_no_slot += 1
                continue
            try:
                data = await sticker.read()
                await guild_to.create_sticker(
                    name=name,
                    description=(sticker.description or name)[:100],
                    emoji=sticker.emoji or name,
                    file=discord.File(io.BytesIO(data), filename=f"{name}.{ext}"))
                free_slots -= 1
                created += 1
                print_add(
                    f"The sticker {Fore.YELLOW}{name}{Fore.BLUE} has been created."
                )
                await asyncio.sleep(1.5)
            except discord.Forbidden:
                print_error(
                    f"Error creating the sticker: {Fore.YELLOW}{name}{Fore.RED} Insufficient permissions.{Fore.RESET}"
                )
                await asyncio.sleep(random.uniform(2, 3))
            except discord.HTTPException as e:
                # 30039 = maximum number of stickers reached
                if getattr(e, 'code', None) == 30039:
                    free_slots = 0
                    skipped_no_slot += 1
                    print_warning(
                        f"Destination ran out of sticker slots at {name}.")
                else:
                    print_warning(f"Could not create sticker {name}: {e}")
                await asyncio.sleep(2)
            except Exception as e:
                print_error(f"Unexpected error with sticker {name}: {e}")

        summary = f"Stickers: {created} cloned"
        if skipped_no_slot:
            summary += f", {skipped_no_slot} skipped because the destination has no free slots"
        (print_warning if skipped_no_slot else print_add)(summary)

    @staticmethod
    async def guild_edit(guild_to: discord.Guild, guild_from: discord.Guild):
        try:
            await guild_to.edit(name=guild_from.name)
            if guild_from.icon:
                try:
                    icon_content = await guild_from.icon.read()
                    await guild_to.edit(icon=icon_content)
                    print_add(f"Guild icon changed: {guild_to.name}")
                except Exception:
                    print_error(
                        f"Error changing the guild icon: {guild_to.name}")
        except discord.Forbidden:
            print_error(f"Error editing the guild: {guild_to.name}")
        except discord.HTTPException as e:
            print_error(f"Error editing the guild: {e}")


def print_add(message):
    ui.ok(message)


def print_delete(message):
    ui.removed(message)


def print_warning(message):
    ui.warn(message)


def print_error(message):
    ui.err(message)