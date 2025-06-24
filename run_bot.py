import json
import time
import threading
from bot_task import (
    Web3, load_config, fetch_and_load_tokens,
    do_swap, add_liquidity, main_swap_all_to_eth,
    send_telegram_message, get_account_name
)

def run_task(task, account, private_key, proxy):
    """Run a single task for an account."""
    try:
        if task["type"] == "swap":
            for _ in range(task["repeat"]):
                do_swap(task["from"], task["to"], 
                       Web3.to_wei(task["amount"], 'ether'))
                time.sleep(task["delay"])
                
        elif task["type"] == "add_liquidity":
            for _ in range(task["repeat"]):
                add_liquidity(task["token"], 
                            Web3.to_wei(task["eth_amount"], 'ether'))
                time.sleep(task["delay"])
                
        elif task["type"] == "swap_all_to_eth":
            for _ in range(task["repeat"]):
                main_swap_all_to_eth()
                time.sleep(task["delay"])
                
    except Exception as e:
        error_msg = f"Error running task for {get_account_name(account)}: {str(e)}"
        print(error_msg)
        send_telegram_message(error_msg)

def main():
    # Load configuration
    config = load_config()
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(config["rpc"]))
    if not w3.is_connected():
        raise Exception("Failed to connect to RPC")
    
    # Load tokens
    fetch_and_load_tokens()
    
    # Send start notification
    start_msg = f"""
🚀 Bot Started
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
👥 Total Wallets: {len(config['accounts'])}
"""
    send_telegram_message(start_msg)
    
    # Create threads for each account
    threads = []
    for account in config["accounts"]:
        thread = threading.Thread(
            target=lambda: [
                run_task(task, account["private_key"], account["private_key"], account["proxy"])
                for task in config["auto_tasks"]["tasks"]
            ]
        )
        threads.append(thread)
        thread.start()
        time.sleep(2)  # Delay between starting threads
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Send completion notification
    end_msg = f"""
✅ Bot Completed
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
👥 Total Wallets: {len(config['accounts'])}
"""
    send_telegram_message(end_msg)

if __name__ == "__main__":
    main() 