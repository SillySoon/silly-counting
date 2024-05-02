# Description: Main file for the bot. Contains the main logic for the bot.
# Created by: SillySoon https://github.com/SillySoon

# Importing necessary libraries
import disnake
from disnake.ext import commands, tasks
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from dotenv import load_dotenv
import helper.database as db
import helper.error as error

# Load the environment variables from the .env file
load_dotenv()

# Accessing the environment variables
discord_token = os.getenv('DISCORD_TOKEN')
command_prefix = os.getenv('COMMAND_PREFIX')
embed_color = int(os.getenv('EMBED_COLOR'), 16)

# Initialize the Bot with command prefix and intents
intents = disnake.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

# Setup basic configuration for logging
os.makedirs('./logs', exist_ok=True)  # Ensure the directory for logs exists

# Setup handler for rotating logs daily
log_handler = TimedRotatingFileHandler(
    filename='./logs/log',  # Base file name
    when='midnight',  # Rotate at midnight
    interval=1,  # Every 1 day
    backupCount=31  # Keep 1 month of logs
)
log_handler.setFormatter(logging.Formatter('%(levelname)s - %(asctime)s - %(message)s'))
log_handler.setLevel(logging.INFO)

# Setup the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# Use `logger` to log messages
logger.info("[START] Bot is starting up...")

# Emojis for reactions
POSITIVE_EMOJI = '<:positive:1232460365183582239>'
NEGATIVE_EMOJI = '<:negative:1232460363954651177>'


# Event listener for when the bot is ready
@bot.event
async def on_ready():
    logger.info("[BOT] Bot is starting up and preparing database...")
    db.setup_database()
    logger.info(f'[BOT] Logged on as {bot.user}!')
    update_status.start()
    print("Bot ready!")


# Task to update the bot's status every 30 minutes
@tasks.loop(minutes=30)
async def update_status():
    status_list = ["/help"]
    activity = disnake.Game(name='/help')
    await bot.change_presence(activity=activity, status=disnake.Status.online)


# Event listener for when a message is sent
@bot.event
async def on_message(message):
    if message.author == bot.user or not message.content.isdigit():
        await bot.process_commands(message)
        return

    if await db.is_channel_allowed(message):
        current_count, last_user_id = db.get_current_count(message.channel.id)

        print(f"[{message.channel.id}] {message.author.id}: {message.content}")
        logger.info(f"[{message.channel.id}] {message.author.id}: {message.content}")

        try:
            message_number = int(message.content)
            if message_number == current_count + 1 and str(message.author.id) != last_user_id:
                db.update_count(message.channel.id, message_number, message.author.id)
                await message.add_reaction(POSITIVE_EMOJI)
            else:
                if str(message.author.id) == last_user_id:
                    db.update_count(message.channel.id, 0, 0)
                    await message.add_reaction(NEGATIVE_EMOJI)
                    embed = disnake.Embed(
                        title="You cannot count twice in a row!",
                        description="Starting from `1` again.",
                        color=disnake.Colour(embed_color)
                    )
                    await message.reply(embed=embed)
                else:
                    db.update_count(message.channel.id, 0, 0)
                    await message.add_reaction(NEGATIVE_EMOJI)
                        title=f"The number was {current_count + 1}",
                        description=f"Starting from `1` again.",
                        color=disnake.Colour(embed_color)
                    )
                    await message.reply(embed=embed)

                """Check if current highscore is less than new highscore and update it."""
                current_highscore = db.get_highscore(message.channel.id)

                if current_count <= current_highscore:
                    embed = disnake.Embed(
                        title="Better luck next time!",
                        description=f"Current highscore is {current_highscore}. Try to beat it!",
                        color=disnake.Colour(embed_color)
                    )
                    await message.channel.send(embed=embed)
                    return

                db.update_highscore(message.channel.id, current_count)
                embed = disnake.Embed(
                    title="New highscore!",
                    description=f"We reached a highscore of `{current_count}`!",
                    color=disnake.Colour(embed_color)
                )
                await message.channel.send(embed=embed)
        except ValueError:
            pass  # Ignore messages that are not numbers

    await bot.process_commands(message)


# Command to add a channel
@bot.slash_command(description='Enables the counting function in XYZ channel.')
@commands.has_permissions(administrator=True)
async def enable(interaction: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel):
    try:
        logger.info(f"[{interaction.channel.id}] {interaction.author.id}: /enable {channel.id} ({interaction.id})")

        if db.check_channel(str(channel.id)):
            embed = disnake.Embed(
                title="Sorry!",
                description=f"Channel <#{channel.id}> is already a counting channel.",
                color=disnake.Colour(embed_color)
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        db.add_channel(str(channel.id))
        embed = disnake.Embed(
            title="Channel Added",
            description=f"Channel <#{channel.id}> successfully added!",
            color=disnake.Colour(embed_color)
        )
        await interaction.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"[BOT] Error when adding channel: {e}")
        await interaction.send(embed=error.create_error_embed(str(e)), ephemeral=True)


# Command to remove a channel
@bot.slash_command(description='Disables the counting function in XYZ channel.')
@commands.has_permissions(administrator=True)
async def disable(interaction: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel):
    try:
        logger.info(f"[{interaction.channel.id}] {interaction.author.id}: /disable {channel.id} ({interaction.id})")

        if not db.check_channel(str(channel.id)):
            embed = disnake.Embed(
                title="Sorry!",
                description=f"Channel <#{channel.id}> is not a counting channel.",
                color=disnake.Colour(embed_color)
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        db.remove_channel(str(channel.id))
        embed = disnake.Embed(
            title="Channel Removed",
            description=f"Channel <#{channel.id}> successfully removed!",
            color=disnake.Colour(embed_color)
        )
        await interaction.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"[BOT] Error when removing channel: {e}")
        await interaction.send(embed=error.create_error_embed(str(e)), ephemeral=True)


# Command to show the highscore
@bot.slash_command(description='Show the highscore of the current channel.')
async def highscore(interaction: disnake.ApplicationCommandInteraction):
    try:
        logger.info(f"[{interaction.channel.id}] {interaction.author.id}: /highscore ({interaction.id})")

        # Check if the channel is allowed for counting
        if not await db.is_channel_allowed(interaction):
            embed = disnake.Embed(
                title="Sorry!",
                description=f"This channel is not activated for counting.",
                color=disnake.Colour(embed_color)
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        # Get the current highscore from the database
        current_highscore = db.get_highscore(interaction.channel.id)
        embed = disnake.Embed(
            title="Highscore",
            description=f"The current highscore is `{current_highscore}`",
            color=disnake.Colour(embed_color)
        )
        await interaction.send(embed=embed)
    # Catch any exceptions and send an error message
    except Exception as e:
        logger.error(f"[BOT] Error when getting highscore: {e}")
        await interaction.send(embed=error.create_error_embed(str(e)), ephemeral=True)


# Command to reset the highscore
@bot.slash_command(description='Reset the highscore of the current channel.')
@commands.has_permissions(administrator=True)
async def reset_highscore(interaction: disnake.ApplicationCommandInteraction):
    try:
        logger.info(f"[{interaction.channel.id}] {interaction.author.id}: /reset_highscore ({interaction.id})")

        # Check if the channel is allowed for counting
        if not await db.is_channel_allowed(interaction):
            embed = disnake.Embed(
                title="Sorry!",
                description=f"This channel is not activated for counting.",
                color=disnake.Colour(embed_color)
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        # Reset the highscore in the database
        db.update_highscore(interaction.channel.id, 0)
        embed = disnake.Embed(
            title="Highscore Reset",
            description=f"Highscore successfully reset!",
            color=disnake.Colour(embed_color)
        )
        await interaction.send(embed=embed)
    # Catch any exceptions and send an error message
    except Exception as e:
        logger.error(f"[BOT] Error when resetting highscore: {e}")
        await interaction.send(embed=error.create_error_embed(str(e)), ephemeral=True)


# Command to set the counter
@bot.slash_command(description='Set the current counter of current channel.')
@commands.has_permissions(administrator=True)
async def set_counter(interaction: disnake.ApplicationCommandInteraction, count: int):
    try:
        logger.info(f"[{interaction.channel.id}] {interaction.author.id}: /set_counter {count} ({interaction.id})")

        # Check if the channel is allowed for counting
        if not await db.is_channel_allowed(interaction):
            embed = disnake.Embed(
                title="Sorry!",
                description=f"This channel is not activated for counting.",
                color=disnake.Colour(embed_color)
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        # Set the counter in the database
        db.update_count(interaction.channel.id, count, 0)
        embed = disnake.Embed(
            title="Counter Set",
            description=f"Counter successfully set to {count}!",
            color=disnake.Colour(embed_color)
        )
        await interaction.send(embed=embed)
    # Catch any exceptions and send an error message
    except Exception as e:
        logger.error(f"[BOT] Error when setting counter: {e}")
        await interaction.send(embed=error.create_error_embed(str(e)), ephemeral=True)


# Bot starts running here
bot.run(discord_token)
