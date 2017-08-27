import logging
import os

from discord.ext import commands

import frontend
from backend import Backend

logging.basicConfig(level=getattr(logging, os.environ.get('loglevel', 'INFO'), logging.INFO))
logger = logging.getLogger(__name__)


def main():
    bot = commands.Bot(command_prefix='')
    logger.info('Initialising backend')
    backend = Backend(bot.loop)
    logger.info('Adding commands')
    frontend.setup(bot, backend)

    @bot.event
    async def on_ready():
        logger.info('Logged in, running check')
        await bot.get_cog('Subscriptions').real_check()

    @bot.event
    async def on_message(message):
        # PMs only
        # todo: check for self message
        if message.channel.is_private:
            logger.info(f"Handling commands in {message.author.name}({message.author.id})'s message: {message.content}")
            await bot.process_commands(message)
        else:
            logger.info(f"Ignoring message: {message.content} because it wasn't in a dm")

    @bot.event
    async def on_command_error(exception, context):
        if isinstance(exception, commands.CommandNotFound):
            await bot.send_message(context.message.channel,  '{} is an unknown command, check your speeling\nFor help type "help"'.format(context.invoked_with))
        elif isinstance(exception, commands.UserInputError):
            await bot.send_message(context.message.channel, 'Bad arguments, check your speeling\nFor help on a command type "help <command>"')
        elif isinstance(exception, commands.CommandOnCooldown):
            await bot.send_message(context.message.channel, str(exception))
        else:
            logger.error(f'Ignoring exception in command {context.command}', exc_info=(type(exception), exception, exception.__traceback__))

    logger.info('Starting bot')
    try:
        bot.run(os.environ.get('discord'))
    finally:
        bot.logout()

if __name__ == '__main__':
    main()
