import sys
import traceback
from configparser import ConfigParser

from discord.ext import commands

import frontend
from backend import Backend

config = ConfigParser()
config.read('config.ini')

def main():
    bot = commands.Bot(command_prefix='')
    backend = Backend(bot.loop)
    frontend.setup(bot, backend)

    @bot.event
    async def on_ready():
        print('Logged in')

    @bot.event
    async def on_message(message):
        # PMs only
        if message.channel.is_private:
            # Handle commands
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
            print('Ignoring exception in command {}'.format(context.command), file=sys.stderr)
            traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)

    try:
        bot.run(config['discord']['token'])
    finally:
        bot.logout()

if __name__ == '__main__':
    main()
