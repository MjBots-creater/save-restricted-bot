# 🔓 Save Restricted Content Bot

Telegram bot that bypasses forwarding restrictions with revenue generation features

## Features
- Forward restricted content to channels
- Personal delivery option
- Force subscription to channels/groups
- Shortener URL verification for revenue
- Owner controls for:
  - Force-sub channels/groups
  - Verification interval
  - Broadcast messages
- MongoDB database
- 24/7 deployment on Render.com

## Setup

### 1. Clone Repository
       
       git clone https://github.com/MjBots-creater/save-restricted-bot.git
       cd save-restricted-bot

### 2. Install Dependencies
       
       pip install -r requirements.txt


### 3. Configure Environment
      Rename .env.sample to .env

     Fill in your credentials:
    
    env
    TELEGRAM_TOKEN=your_bot_token
    MONGO_URI=your_mongodb_uri
    OWNER_ID=your_telegram_id
    WEBHOOK_URL=https://your-app.onrender.com
    SHORTENER_API_URL=https://your-shortener-api.com/api
    SHORTENER_API_KEY=your_api_key
    VERIFICATION_INTERVAL=24



### 4. Run the Bot
      
      python bot.py

### Deployment to Render.com
    Create new Web Service at render.com

    Connect your GitHub repository

    Set environment variables:

    TELEGRAM_TOKEN - From @BotFather

    MONGO_URI - MongoDB connection string

    OWNER_ID - Your Telegram ID

    SHORTENER_API_URL - Your shortener API endpoint

    SHORTENER_API_KEY - Your shortener API key

    VERIFICATION_INTERVAL - Hours between verifications (default: 24)

    PORT = 8443


### After first deploy, set WEBHOOK_URL to your app URL

    Owner Commands
    /addfchannel @channel - Add force-sub channel

    /addfgroup @group - Add force-sub group

    /removefchannel @channel - Remove force-sub channel

    /removefgroup @group - Remove force-sub group

    /setverifyinterval <hours> - Set verification interval

    /setshortener <api_url> <api_key> - Configure shortener API

    /broadcast <message> - Message all users

    /resetall - Reset all data

### Keep Bot Active 24/7
    Create free account at UptimeRobot

    Add HTTP monitor with 5-minute interval

    Use your Render app URL as monitor target

### Revenue Generation
Non-premium users must verify periodically

Verification uses your configured shortener

Earn from ad views and clicks

Premium users bypass verification

### Support
For issues, contact @your_telegram_username
