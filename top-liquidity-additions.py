
import re
import asyncio
import json
import logging
import aiohttp
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import RetryAfter
from html import escape
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Your bot token from the BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN"

# OAuth Token
OAUTH_TOKEN = "YOUR_OAUTH_TOKEN"

# Function to split long text into smaller parts
def split_text(text, max_length):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# Function to send a long message as multiple smaller messages
async def send_long_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_generator):
    for part in message_generator:  # Use a regular 'for' loop since this is a normal generator
        while True:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=part,
                    parse_mode=ParseMode.HTML
                )
                break  # Break the loop if the message is sent successfully
            except RetryAfter as e:
                logging.warning(f"Flood control exceeded. Retrying in {e.retry_after} seconds.")
                await asyncio.sleep(e.retry_after)  # Wait for the specified time before retrying


async def send_query_and_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = 'https://streaming.bitquery.io/eap'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OAUTH_TOKEN}'
    }
    query = """ 
            query ($time_5min_ago: DateTime) {
  Solana {
    DEXPools(
      limit: {count: 10}
      orderBy: {descending: Block_Time, descendingByField: "Pool_Base_addedLiquidity"}
      where: {Pool: {Base: {ChangeAmount: {gt: "0"}}, Market: {QuoteCurrency: {MintAddress: {in: ["So11111111111111111111111111111111111111112", "11111111111111111111111111111111"]}}}}, Transaction: {Result: {Success: true}}, Block: {Time: {since: $time_5min_ago}}}
    ) {
      Pool {
        Market {
          MarketAddress
          BaseCurrency {
            MintAddress
            Symbol
            Name
          }
          QuoteCurrency {
            MintAddress
            Symbol
            Name
          }
        }
        Dex {
          ProtocolFamily
          ProtocolName
        }
        Quote {
          PostAmount
          PriceInUSD
          PostAmountInUSD
        }
        Base {
          addedLiquidity: ChangeAmount
          PostAmount
        }
      }
    }
  }
}

"""  # Truncated for brevity

    now = datetime.now(timezone.utc)
    time_5min_ago = now - timedelta(minutes=5)

    variables = {
        "time_5min_ago": time_5min_ago.isoformat()
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json={'query': query, 'variables': variables}) as response:
            response_text = await response.text()

            if response.status == 200:
                try:
                    response_json = json.loads(response_text)
                    solana_data = response_json.get('data', {}).get('Solana', {}).get('DEXPools', [])
                    print(len(solana_data))

                    # Send formatted message parts as a generator
                    formatted_message = format_message(solana_data)
                    await send_long_message(update, context, formatted_message)
                        
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse JSON. Response: {response_text}")
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="Failed to retrieve data.")
            else:
                logging.error(f"Request failed with status {response.status}")
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"API request failed with status code {response.status}.")


def format_message(data):
    message = ""
    for pool in data:
        try:
            # Market details
            base_currency_symbol = escape(pool['Pool']['Market']['BaseCurrency'].get('Symbol', "N/A"))
            base_currency_mint = escape(pool['Pool']['Market']['BaseCurrency'].get('MintAddress', "N/A"))
            
            quote_currency_symbol = escape(pool['Pool']['Market']['QuoteCurrency'].get('Symbol', "N/A"))
            quote_currency_mint = escape(pool['Pool']['Market']['QuoteCurrency'].get('MintAddress', "N/A"))
            
            market_address = escape(pool['Pool']['Market'].get('MarketAddress', "N/A"))
            
            # Dex protocol details
            protocol_family = escape(pool['Pool']['Dex'].get('ProtocolFamily', "N/A"))
            protocol_name = escape(pool['Pool']['Dex'].get('ProtocolName', "N/A"))
            
            # Base currency liquidity details
            base_post_amount = pool['Pool']['Base'].get('PostAmount', "0")
            added_liquidity = pool['Pool']['Base'].get('addedLiquidity', "0")

            # URL for Trade Now button
            trade_now_url = f"https://dexrabbit.com/solana/pair/{base_currency_mint}/{quote_currency_mint}"

            # Formatting the message part
            message_part = (
                f"<b><a href='https://dexrabbit.com/solana/token/{base_currency_mint}'>{base_currency_symbol}</a></b> | "
                f"<b><a href='https://dexrabbit.com/solana/token/{quote_currency_mint}'>{quote_currency_symbol}</a></b>\n"
                f"📈 <b>Added Liquidity:</b> {added_liquidity}\n"
                f"⏳ <b>Liquidity after addition:</b> {base_post_amount}\n"
                f"🔄 <b>DEX:</b> {protocol_family}\n"
                f"<a href='{trade_now_url}'>💵 Trade Now</a>\n"
                "----------------------------------\n"
            )

            # Check if adding this message part will exceed Telegram's message length limit
            if (len(message) + len(message_part)) > 4096:
                # If the message exceeds the limit, send the current message and reset
                logging.warning("Message length exceeded, sending part of the message.")
                yield message  # Return the current message part
                message = ""  # Reset message for next part

            message += message_part
            
        except Exception as e:
            logging.error(f"Error formatting message for pool: {pool}. Error: {str(e)}")
            continue  # Skip this item if there's an error in formatting

    yield message  # Return the remaining message if any

# Add a global flag to prevent multiple tasks from running
is_task_running = False

async def start_regular_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_task_running
    if is_task_running:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Task already running.")
        return

    is_task_running = True  # Set the flag to indicate that the task is running
    try:
        while True:
            await send_query_and_process(update, context)
            await asyncio.sleep(1800)  # Wait for 30 minutes before sending the next request
    finally:
        is_task_running = False  # Ensure the flag is reset if the loop ends for any reason

# Command handler to start the regular requests
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Starting regular requests every 4 minutes...")
    asyncio.create_task(start_regular_requests(update, context))

# Main function to set up the Telegram bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    application.run_polling()
