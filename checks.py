import logging
from discord.ext import commands

logger = logging.getLogger(__name__)


def is_owner():
    def f(ctx):
        if ctx.message.author.id == '132184348639100929':
            logger.info(f'Running admin command from {ctx.message.author.name}({ctx.message.author.id})')
            return True
        else:
            logger.info(f'Not running admin command from {ctx.message.author.name}({ctx.message.author.id})')
            return False
    return commands.check(f)
