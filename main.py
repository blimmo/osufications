import logging
import os
from configparser import ConfigParser

from discord.ext import commands

import frontend
from backend import Backend

logging.basicConfig(level=getattr(logging, os.environ.get('loglevel', 'INFO'), logging.INFO))
logger = logging.getLogger(__name__)

conf = ConfigParser()
conf.read('msgs.ini')
msgs = conf['messages']


def main():
    bot = commands.Bot(command_prefix='')
    logger.info('Initialising backend')
    backend = Backend(bot.loop)
    logger.info('Adding commands')
    frontend.setup(bot, backend)

    @bot.event
    async def on_ready():
        logger.info('Logged in, starting initial check')
        await bot.get_cog('Subscriptions').real_check()

    @bot.event
    async def on_message(message):
        if not message.channel.is_private:
            logger.info(f"Ignoring message: {message.content} because it wasn't in a dm")
        elif message.author == bot.user:
            logger.info(f"Ignoring own message: {message.content}")
        else:
            logger.info(f"Handling commands in {message.author.name}({message.author.id})'s message: {message.content}")
            await bot.process_commands(message)

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

    @bot.event
    async def on_member_join(member):
        if member.server.id == '351839594041442314':
            logger.info(f'{member.name}({member.id}) joined the server sending initial messages')
            await bot.send_message(member, msgs['start'])
            await bot.pin_message(await bot.send_message(member, msgs['pin'].format(os.environ.get('url'))))

    logger.info('Starting bot')
    bot.run(os.environ.get('discord'))

if __name__ == '__main__':
    main()
