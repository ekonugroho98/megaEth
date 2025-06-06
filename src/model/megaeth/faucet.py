import asyncio
from loguru import logger
import random
import primp
from src.model.help.captcha import Capsolver, Solvium, AntiCaptcha
from src.utils.config import Config
from eth_account import Account
import hashlib
from curl_cffi.requests import AsyncSession
import json
import platform
from pynocaptcha import CloudFlareCracker, TlsV1Cracker
from decimal import Decimal
from web3 import Web3
from src.utils.telegram_logger import send_telegram_message

from src.utils.decorators import retry_async


@retry_async(default_value=False)
async def faucet(
    session: primp.AsyncClient,
    account_index: int,
    config: Config,
    wallet: Account,
    proxy: str,
) -> bool:

    try:
        # Get initial balance
        initial_balance = await get_eth_balance(wallet.address)

        logger.info(
            f"[{account_index}] | Starting faucet for account {wallet.address}..."
        )

        if config.FAUCET.USE_ANTICAPTCHA:
            logger.info(
                f"[{account_index}] | Solving Cloudflare challenge with Anti-Captcha..."
            )
            anticaptcha = AntiCaptcha(
                api_key=config.FAUCET.ANTICAPTCHA_API_KEY,
                proxy=proxy,
            )
            cf_result = await anticaptcha.solve_turnstile(
                "0x4AAAAAABA4JXCaw9E2Py-9",
                "https://testnet.megaeth.com/",
            )
        elif config.FAUCET.USE_CAPSOLVER:
            logger.info(
                f"[{account_index}] | Solving Cloudflare challenge with Capsolver..."
            )
            capsolver = Capsolver(
                api_key=config.FAUCET.CAPSOLVER_API_KEY,
                proxy=proxy,
                session=session,
            )
            cf_result = await capsolver.solve_turnstile(
                "0x4AAAAAABA4JXCaw9E2Py-9",
                "https://testnet.megaeth.com/",
            )
        else:
            logger.info(
                f"[{account_index}] | Solving Cloudflare challenge with Solvium..."
            )
            solvium = Solvium(
                api_key=config.FAUCET.SOLVIUM_API_KEY,
                session=session,
                proxy=proxy,
            )
            
            result = await solvium.solve_captcha(
                sitekey="0x4AAAAAABA4JXCaw9E2Py-9",
                pageurl="https://testnet.megaeth.com/",
            )
            cf_result = result

        if not cf_result:
            raise Exception("Failed to solve Cloudflare challenge")

        logger.success(f"[{account_index}] | Cloudflare challenge solved")

        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5",
            "content-type": "text/plain;charset=UTF-8",
            "origin": "https://testnet.megaeth.com",
            "priority": "u=1, i",
            "referer": "https://testnet.megaeth.com/",
            "sec-ch-ua": '"Chromium";v="131", "Not:A-Brand";v="24", "Google Chrome";v="131"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        data = f'{{"addr":"{wallet.address}","token":"{cf_result}"}}'

        curl_session = AsyncSession(
            impersonate="chrome131",
            proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
            verify=False,
        )

        claim_result = await curl_session.post(
            "https://carrot.megaeth.com/claim",
            headers=headers,
            data=data,
        )
        response_text = claim_result.text
        status_code = claim_result.status_code
    
        logger.info(
            f"[{account_index}] | Received response with status code: {status_code}"
        )

        if claim_result.json()['success']:
            # Get new balance after claim
            new_balance = await get_eth_balance(wallet.address)
            balance_increase = new_balance - initial_balance
            
            logger.success(
                f"[{account_index}] | Successfully got tokens from faucet. Balance increased by {balance_increase:.6f} ETH"
            )
            
            # Send detailed notification
            if config.SETTINGS.SEND_TELEGRAM_LOGS:
                message = (
                    f"💧 Faucet Claim Success\n\n"
                    f"💳 Wallet: {account_index} | <code>{wallet.address[:6]}...{wallet.address[-4:]}</code>\n"
                    f"💰 Balance Increase: {balance_increase:.6f} ETH\n"
                    f"💵 New Balance: {new_balance:.6f} ETH"
                )
                await send_telegram_message(config, message)
            return True

        if "less than 24 hours have passed" in response_text:
            logger.success(
                f"[{account_index}] | Less than 24 hours have passed since last claim, wait..."
            )
            return True

        if "used Cloudflare to restrict access" in response_text:
            raise Exception("your proxy IP is blocked by Cloudflare. Try to change your proxy")

        if not response_text:
            raise Exception("Failed to send claim request")

        if '"Success"' in response_text:
            # Get new balance after claim
            new_balance = await get_eth_balance(wallet.address)
            balance_increase = new_balance - initial_balance
            
            logger.success(
                f"[{account_index}] | Successfully got tokens from faucet. Balance increased by {balance_increase:.6f} ETH"
            )
            
            # Send detailed notification
            if config.SETTINGS.SEND_TELEGRAM_LOGS:
                message = (
                    f"💧 Faucet Claim Success\n\n"
                    f"💳 Wallet: {account_index} | <code>{wallet.address[:6]}...{wallet.address[-4:]}</code>\n"
                    f"💰 Balance Increase: {balance_increase:.6f} ETH\n"
                    f"💵 New Balance: {new_balance:.6f} ETH"
                )
                await send_telegram_message(config, message)
            return True

        if "Claimed already" in response_text:
            logger.success(
                f"[{account_index}] | Already claimed tokens from faucet"
            )
            return True

        else:
            logger.error(
                f"[{account_index}] | Failed to get tokens from faucet: {response_text}"
            )
        await asyncio.sleep(3)

    except Exception as e:
        random_pause = random.randint(
            config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
            config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
        )
        if "operation timed out" in str(e):
            logger.error(
                f"[{account_index}] | Error faucet to megaeth.com: Connection timed out. Next faucet in {random_pause} seconds"
            )
        else:
            logger.error(
                f"[{account_index}] | Error faucet to megaeth.com: {e}. Next faucet in {random_pause} seconds"
            )
        await asyncio.sleep(random_pause)
        raise


async def get_eth_balance(address: str) -> Decimal:
    """Get ETH balance for the wallet address"""
    web3 = Web3(Web3.HTTPProvider("https://carrot.megaeth.com/rpc"))
    balance_wei = web3.eth.get_balance(address)
    return Decimal(web3.from_wei(balance_wei, 'ether'))

