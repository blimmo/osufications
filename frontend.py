import inspect
import traceback
from configparser import ConfigParser

import discord
from discord.ext import commands
from osuapi.enums import BeatmapStatus

import checks

urlfmt = 'http://osu.ppy.sh/s/{0.beatmapset_id}'
thumbfmt = 'http://b.ppy.sh/thumb/{0.beatmapset_id}l.jpg'
icon_urls = {BeatmapStatus.ranked: 'http://i.imgur.com/5r5hs7L.png',
             BeatmapStatus.approved: 'http://i.imgur.com/5r5hs7L.png',
             BeatmapStatus.qualified: 'http://i.imgur.com/qsOb44F.png',
             BeatmapStatus.loved: 'http://i.imgur.com/gBXSNJQ.png',
             BeatmapStatus.pending: 'http://i.imgur.com/hNuc9Ci.png',
             }
osu_pink = 0xff67aa

listfmt = '{0}: {attr} "{value}"'

conf = ConfigParser()
conf.read('msgs.ini')
msgs = conf['messages']
notif = conf['notification']


class Subscriptions:
    """Commands to control the notifications you get"""

    def __init__(self, bot, backend):
        self.bot = bot
        self.backend = backend

    @commands.command(pass_context=True)
    async def sub(self, ctx, attribute: str, value: str):
        """Add a subscription
        Where attribute is the thing you want to check and value what you want to check it for"""
        try:
            self.backend.add(ctx.message.author.id, attribute, value)
        except ValueError as e:
            await self.bot.say(msgs['invalid_type'].format(e))
        else:
            await self.bot.say(msgs['add_sub'].format(attribute, value))

    @commands.command(name='list', pass_context=True)
    async def list_subs(self, ctx):
        """Lists the subscriptions you have associated with your account"""
        substrs = (listfmt.format(i, **doc)
                   for i, doc in enumerate(self.backend.list(ctx.message.author.id)))
        msg = '\n'.join(substrs)
        if msg == '':
            msg = msgs['empty_list']
        await self.bot.say(msg)

    @commands.command(pass_context=True)
    async def remove(self, ctx, index: int):
        """Removes a subscription
        Where index is the number that appeared before it in list"""
        removed = self.backend.remove(ctx.message.author.id, index)
        await self.bot.say(msgs['removed'].format(**removed))

    @commands.command(pass_context=True)
    async def remove_all(self, ctx):
        """Removes all your subscriptions and removes your account from the database"""
        self.backend.remove_all(ctx.message.author.id)

    @commands.command()
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def check(self):
        """Force a check of everybody's subscriptions now
        Has a cooldown of 1 minute
        You shouldn't need to use this as it's called automatically"""
        await self.bot.type()
        await self.backend.check(self.notify)

    async def notify(self, user_id, beatmaps, sub=None):
        """Sends the user with user_id a notification about the beatmapset beatmaps caused by their subscription sub"""
        beatmap = beatmaps[0]
        beatmaps = sorted(beatmaps, key=lambda b: b.difficultyrating)
        embed = discord.Embed(title=notif['title'].format(beatmap),
                              url=urlfmt.format(beatmap),
                              description=notif['desc'].format(beatmap, *divmod(beatmap.total_length, 60)),
                              color=osu_pink)
        embed.set_author(name=notif['header'].format(beatmap.approved.name.title()),
                         icon_url=icon_urls[beatmap.approved])
        embed.set_image(url=thumbfmt.format(beatmap))
        embed.add_field(name=notif['diff'],
                        value='\n'.join('{.version}'.format(b) for b in beatmaps),
                        inline=True)
        embed.add_field(name=notif['stars'],
                        value='\n'.join('{.difficultyrating:.3}'.format(b) for b in beatmaps),
                        inline=True)
        embed.set_footer(text=notif['footer'].format(**sub),
                         icon_url='https://w.ppy.sh/c/c9/Logo.png')
        await self.bot.send_message(await self.bot.get_user_info(user_id), embed=embed)


class Admin:
    """Admin only commands"""

    def __init__(self, bot, backend):
        self.bot = bot
        self.backend = backend

    @commands.command(hidden=True)
    @checks.is_owner()
    async def start_msg(self, user: str):
        await self.bot.send_message(await self.bot.get_user_info(user), msgs['start'])

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def eval(self, ctx, *, code: str):
        """Evaluates code."""
        code = code.strip('` ')
        python = '```py\n{}\n```'
        result = None

        try:
            result = eval(code)
            if inspect.isawaitable(result):
                result = await result
        except Exception:
            await self.bot.say(python.format(traceback.format_exc()))
            return

        await self.bot.say(python.format(result))


def setup(bot, backend):
    bot.add_cog(Subscriptions(bot, backend))
    bot.add_cog(Admin(bot, backend))
