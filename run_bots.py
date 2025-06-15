import os
import time
from bot_faucet import main as run_faucet
from bot_task import main_auto_all_tasks

def main():
    bot_type = os.getenv('BOT_TYPE', 'faucet')
    
    if bot_type == 'task':
        print("Starting Task Bot in auto mode...")
        while True:
            try:
                main_auto_all_tasks()
                # Wait for 1 hour before next run
                time.sleep(3600)
            except Exception as e:
                print(f"Error in task bot: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    else:
        print("Starting Faucet Bot...")
        run_faucet()

if __name__ == "__main__":
    main() 