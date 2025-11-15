"""
Quick script to force-sync Discord commands to a specific guild (server).
This bypasses Discord's global sync delay (up to 1 hour).
"""

import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Get your Discord server ID (right-click server name -> Copy Server ID)
GUILD_ID = input("Enter your Discord Server ID (or press Enter to skip): ").strip()

async def sync_commands():
    """Force sync commands to guild or globally"""
    
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'\n✅ Logged in as {bot.user}')
        print(f'📊 Connected to {len(bot.guilds)} server(s)\n')
        
        try:
            if GUILD_ID:
                # Guild-specific sync (instant!)
                guild = discord.Object(id=int(GUILD_ID))
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                print(f'✅ Synced {len(synced)} commands to guild {GUILD_ID} (INSTANT)')
            else:
                # Global sync (takes up to 1 hour)
                synced = await bot.tree.sync()
                print(f'✅ Synced {len(synced)} commands globally (may take up to 1 hour)')
            
            print(f'\n📋 Commands synced:')
            for cmd in synced:
                print(f'  • /{cmd.name}')
            
            print('\n✨ Done! Commands should appear in Discord.')
            print('   If guild-synced: Available immediately')
            print('   If global-synced: May take up to 1 hour\n')
            
        except Exception as e:
            print(f'❌ Error syncing commands: {e}')
        
        await bot.close()
    
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print('❌ DISCORD_BOT_TOKEN not found in .env')
        return
    
    await bot.start(token)

if __name__ == '__main__':
    print('\n' + '='*60)
    print('Discord Command Sync Tool')
    print('='*60)
    print('\nThis will force Discord to register your bot commands.')
    print('\nOptions:')
    print('1. Guild sync (instant) - Enter server ID')
    print('2. Global sync (1 hour) - Press Enter\n')
    
    asyncio.run(sync_commands())

