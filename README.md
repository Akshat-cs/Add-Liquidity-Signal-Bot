# Telegram Bot for Solana Liquidity Monitoring

This Telegram bot retrieves and displays Solana Pools liquidity additions data from the Bitquery API. The bot fetches recent additions in liquidity and provides actionable trade links for the user.

Video Tutorial Link - https://www.youtube.com/watch?v=s5GTjKhUmEo

## Features

- Fetches and displays liquidity additions in Solana DEX pools.
- Provides detailed pool information, including:
  - Base and Quote currencies.
  - Added liquidity and post-liquidity amounts.
  - Protocol details.
- Includes trade links for immediate actions.

## Running Steps

1. Clone this repository and navigate to the project directory:

   ```bash
   git clone https://github.com/Akshat-cs/Add-Liquidity-Signal-Bot
   ```

2. Install the required dependencies:

   ```bash
   pip install python-telegram-bot aiohttp
   ```

3. Replace Bot token and OAuth Token values in the `top-liquidity-additions.py` file with your own tokens. Get the BOT_TOKEN from Bot father and Bitquery OAuth token using these [steps](https://docs.bitquery.io/docs/authorisation/how-to-generate/):

   ```
   BOT_TOKEN=your-telegram-bot-token
    OAUTH_TOKEN=your-bitquery-oauth-token
   ```

4. Start the bot:

   ```
   python top-liquidity-additions.py
   ```

5. Use the `/start` command in your Telegram chat with the bot to begin monitoring Solana pools with liquidity additions.
