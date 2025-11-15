# 🤖 Discord Bot Setup Guide

## ⚠️ IMPORTANT: Your Bot Token Looks Wrong!

Looking at your `.env` file, your `DISCORD_BOT_TOKEN` appears to be incorrect:
```
DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
```

This looks like a **hex string** (64 characters), but Discord bot tokens are usually:
- Much longer (~70+ characters)
- Contain dots (`.`) separating three parts
- Format: `XXXXXXXXX.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXX`

Example of a valid token format:
```
EXAMPLE_TOKEN_FORMAT.123456.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
```

---

## 🔧 How to Get the CORRECT Discord Bot Token

### Step 1: Go to Discord Developer Portal

1. Visit: https://discord.com/developers/applications
2. Log in with your Discord account

### Step 2: Create or Select Your Application

**Option A: Create New Application**
1. Click **"New Application"** (top right)
2. Enter name: `SmartInvest` (or any name)
3. Click **"Create"**

**Option B: Use Existing Application**
1. Click on your existing application in the list

### Step 3: Get the Bot Token

1. Click **"Bot"** in the left sidebar
2. Under **"TOKEN"** section:
   - If you see **"Reset Token"** button: Click it
   - If you see **"Copy"** button: Click it
3. **Copy the token** - it should look like:
   ```
   EXAMPLE_TOKEN_FORMAT.123456.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
   ```
   *(This is a fake example - yours will be different)*

⚠️ **WARNING:** Never share your real token! It gives full control of your bot.

### Step 4: Enable Required Intents

While on the Bot page, scroll down to **"Privileged Gateway Intents"**:

✅ **Enable these:**
- `PRESENCE INTENT` (optional)
- `SERVER MEMBERS INTENT` (optional)
- `MESSAGE CONTENT INTENT` ⭐ **REQUIRED**

Click **"Save Changes"**

### Step 5: Update Your .env File

Replace the token in your `.env` file:

```bash
# OLD (WRONG):
DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# NEW (CORRECT):
DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
```

*(Use YOUR actual token from Step 3)*

---

## 🔗 How to Add Bot to Your Discord Server

### Step 6: Generate OAuth2 URL

1. In Discord Developer Portal, click **"OAuth2"** → **"URL Generator"**
2. **Select SCOPES:**
   - ✅ `bot`
   - ✅ `applications.commands`

3. **Select BOT PERMISSIONS:**
   - ✅ `Send Messages`
   - ✅ `Embed Links`
   - ✅ `Attach Files`
   - ✅ `Read Message History`
   - ✅ `Use Slash Commands`
   - ✅ `Add Reactions` (optional)

4. **Copy the generated URL** at the bottom

### Step 7: Invite Bot to Your Server

1. Paste the URL into your browser
2. Select your Discord server from dropdown
3. Click **"Authorize"**
4. Complete the captcha
5. Bot should now appear in your server (offline for now)

---

## 📋 Get Your Channel ID

Your bot needs to know which channel to post to.

### Method 1: Enable Developer Mode

1. Open Discord
2. Go to **User Settings** ⚙️ (bottom left)
3. Click **"Advanced"**
4. Enable **"Developer Mode"** ✅

### Method 2: Get Channel ID

1. Right-click on the channel you want the bot to use
2. Click **"Copy Channel ID"**
3. Paste it in your `.env` file:

```bash
DISCORD_CHANNEL_ID=YOUR_CHANNEL_ID_HERE  # Replace with your actual channel ID
```

---

## ✅ Final .env File Check

Your `.env` should look like this:

```bash
# Discord Bot Configuration
DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
DISCORD_CHANNEL_ID=YOUR_CHANNEL_ID_HERE

# News API Configuration (optional)
NEWS_API_KEY=YOUR_NEWS_API_KEY_HERE

# Database Configuration
DATABASE_URL=sqlite:///smartinvest_dev.db

# Environment
ENVIRONMENT=development
```

**Check:**
- ✅ Token has dots (`.`) in it
- ✅ Token is 70+ characters
- ✅ Channel ID is all numbers
- ✅ No quotes around values

---

## 🚀 Start Your Bot

Once your `.env` is correct:

```bash
cd /Users/himnish03/Documents/Projects/SmartInvest/smartinvest-bot
source venv/bin/activate
python bot_with_real_data.py
```

**What you should see:**
```
INFO:SmartInvestBot:SmartInvestBot initialized with REAL data components
INFO:discord.gateway:Shard ID None has connected to Gateway...
INFO:SmartInvestBot:SmartInvestBot#1234 has connected to Discord!

============================================================
🤖 SmartInvest Bot Ready (REAL DATA MODE)!
============================================================
Bot Name: SmartInvestBot#1234
ML Model: ⚠️  Not found (using rules)
News API: ✅ Configured
============================================================
```

### If Bot "Just Sticks" (Hangs):

This is **NORMAL!** The bot is running and waiting for commands.

**The bot will:**
- ✅ Stay running (doesn't exit)
- ✅ Show its status in Discord (green dot = online)
- ✅ Wait for slash commands
- ✅ Print logs when commands are used

**DO NOT close the terminal!** Keep it running.

---

## 🎮 Test Your Bot in Discord

1. Go to your Discord server
2. Look for your bot in the member list (should show **online** 🟢)
3. In any channel, type: `/`
4. You should see your bot's commands appear:
   - `/help`
   - `/stock`
   - `/daily`
   - `/refresh`

5. Try: `/help`
6. Bot should respond with an embed!

---

## 🐛 Troubleshooting

### Issue: "Invalid token"
**Cause:** Wrong token format or expired token  
**Fix:** Get new token from Discord Developer Portal (Step 3)

### Issue: Bot shows offline in Discord
**Cause:** 
- Token is wrong
- Bot hasn't been invited to server
- Bot script isn't running

**Fix:**
1. Check token format (should have dots)
2. Invite bot again (Step 7)
3. Make sure script is running

### Issue: Commands don't appear
**Cause:** Slash commands not synced or wrong permissions  
**Fix:**
1. Wait 1-2 minutes after bot starts
2. Make sure bot has `applications.commands` scope
3. Try leaving and rejoining the server
4. Restart the bot

### Issue: "Unknown interaction"
**Cause:** Command was registered but bot restarted  
**Fix:** Wait a few seconds and try again

### Issue: Bot responds but says "No stocks in database"
**Cause:** Haven't run data loading script yet  
**Fix:** Run: `python scripts/load_full_data.py`

---

## 📊 Understanding Bot Behavior

### Normal Behavior:

```bash
$ python bot_with_real_data.py

# Bot starts...
INFO:SmartInvestBot:Bot initialized

# Bot connects...
INFO:discord.gateway:Connected

# Bot is ready...
============================================================
🤖 SmartInvest Bot Ready!
============================================================

# Now it waits here ← THIS IS NORMAL!
# Terminal will show logs when users interact with bot
```

The bot is **supposed to "hang"** - it's running a persistent connection to Discord!

### When Users Use Commands:

```bash
# User types /stock AAPL in Discord

INFO:SmartInvestBot:Scoring AAPL...
INFO:data.collectors:Fetching price data for AAPL
INFO:features.technical:Calculating technical features
# etc...
```

You'll see logs appear in the terminal as the bot works.

---

## 🛑 How to Stop the Bot

Press `Ctrl + C` in the terminal where the bot is running.

```bash
^C
🛑 Bot stopped by user
```

---

## 🔄 Restart the Bot

Just run the command again:

```bash
python bot_with_real_data.py
```

---

## 📝 Quick Checklist

Before running bot, verify:

- [ ] Bot created in Discord Developer Portal
- [ ] Bot token copied (format: `XXX.XXX.XXX` with dots)
- [ ] Message Content Intent enabled
- [ ] Bot invited to your server (with `bot` and `applications.commands` scopes)
- [ ] Channel ID copied from Discord
- [ ] `.env` file updated with correct token and channel ID
- [ ] Virtual environment activated
- [ ] Database initialized (`python -c "from data.database import init_db; init_db()"`)

Then start:
```bash
python bot_with_real_data.py
```

---

## 🎯 Expected Flow

```
1. Get correct bot token from Discord Developer Portal
   ↓
2. Update .env file
   ↓
3. Invite bot to your Discord server
   ↓
4. Get channel ID
   ↓
5. Update .env with channel ID
   ↓
6. Run: python bot_with_real_data.py
   ↓
7. Bot shows "Ready!" and waits (terminal stays open)
   ↓
8. Bot appears online in Discord
   ↓
9. Type /help in Discord
   ↓
10. Bot responds!
```

---

## 🆘 Still Having Issues?

Run this diagnostic:

```bash
python -c "
from config import Config
config = Config()
print('🔍 Bot Configuration Check:')
print()
print(f'Token length: {len(config.DISCORD_BOT_TOKEN)} chars')
print(f'Token format: {config.DISCORD_BOT_TOKEN[:20]}...')
print(f'Has dots: {\".\" in config.DISCORD_BOT_TOKEN}')
print(f'Channel ID: {config.DISCORD_CHANNEL_ID}')
print()
if '.' not in config.DISCORD_BOT_TOKEN:
    print('❌ TOKEN LOOKS WRONG! Should have dots (.)')
    print('   Get new token from Discord Developer Portal')
elif len(config.DISCORD_BOT_TOKEN) < 50:
    print('❌ TOKEN TOO SHORT!')
else:
    print('✅ Token format looks correct')
"
```

This will tell you if your token is formatted correctly!

---

## 📚 Additional Resources

- **Discord Developer Portal:** https://discord.com/developers/applications
- **Discord Bot Guide:** https://discord.com/developers/docs/getting-started
- **Invite Bot Calculator:** https://discordapi.com/permissions.html

---

## ✅ Summary

**The key issue is likely your bot token format!**

1. Get the **correct** token from Discord Developer Portal
2. Update your `.env` file
3. Invite bot to server
4. Run: `python bot_with_real_data.py`
5. Bot will "hang" (this is normal - it's running!)
6. Test with `/help` in Discord

The bot doesn't "load into Discord" - it **connects** to Discord and runs continuously on your machine!

