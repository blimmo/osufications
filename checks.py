from configparser import ConfigParser

from discord.ext import commands

config = ConfigParser()
config.read('config.ini')


def is_owner():
    def f(ctx):
        return ctx.message.author.id == config['ids']['owner']
    return commands.check(f)
