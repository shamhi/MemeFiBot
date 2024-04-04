import asyncio
from time import time
from random import randint
from urllib.parse import unquote

import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw.functions.messages import RequestWebView

from bot.config import settings
from bot.utils import logger
from bot.utils.graphql import Query, OperationName
from bot.utils.boosts import FreeBoostType, UpgradableBoostType
from bot.exceptions import InvalidSession
from .headers import headers


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

        self.GRAPHQL_URL = 'https://api-gw-tg.memefi.club/graphql'

    async def get_tg_web_data(self, proxy: str | None):
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=await self.tg_client.resolve_peer('memefi_coin_bot'),
                bot=await self.tg_client.resolve_peer('memefi_coin_bot'),
                platform='android',
                from_bot_menu=False,
                url='https://tg-app.memefi.club/game'
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            query_id = tg_web_data.split('query_id=', maxsplit=1)[1].split('&user', maxsplit=1)[0]
            user_data = tg_web_data.split('user=', maxsplit=1)[1].split('&auth_date', maxsplit=1)[0]
            auth_date = tg_web_data.split('auth_date=', maxsplit=1)[1].split('&hash', maxsplit=1)[0]
            hash_ = tg_web_data.split('hash=', maxsplit=1)[1]

            me = await self.tg_client.get_me()

            json_data = {
                'operationName': OperationName.MutationTelegramUserLogin,
                'query': Query.MutationTelegramUserLogin,
                'variables': {
                    'webAppData': {
                        'auth_date': int(auth_date),
                        'hash': hash_,
                        'query_id': query_id,
                        'checkDataString': f'auth_date={auth_date}\nquery_id={query_id}\nuser={user_data}',
                        'user': {
                            'id': me.id,
                            'allows_write_to_pm': True,
                            'first_name': me.first_name,
                            'last_name': me.last_name if me.last_name else '',
                            'username': me.username if me.username else '',
                            'language_code': me.language_code if me.language_code else 'en',
                        },
                    },
                }
            }

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return json_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def get_access_token(self, http_client: aiohttp.ClientSession, tg_web_data: dict[str]):
        try:
            response = await http_client.post(url=self.GRAPHQL_URL, json=tg_web_data)
            response.raise_for_status()

            response_json = await response.json()
            access_token = response_json['data']['telegramUserLogin']['access_token']

            return access_token
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting Access Token: {error}")
            await asyncio.sleep(delay=3)

    async def get_profile_data(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                'operationName': OperationName.QUERY_GAME_CONFIG,
                'query': Query.QUERY_GAME_CONFIG,
                'variables': {}
            }

            response = await http_client.post(url=self.GRAPHQL_URL, json=json_data)
            response.raise_for_status()

            response_json = await response.json()
            profile_data = response_json['data']['telegramGameGetConfig']

            return profile_data
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting Profile Data: {error}")
            await asyncio.sleep(delay=3)


    async def set_next_boss(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                'operationName': OperationName.telegramGameSetNextBoss,
                'query': Query.telegramGameSetNextBoss,
                'variables': {}
            }

            response = await http_client.post(url=self.GRAPHQL_URL, json=json_data)
            response.raise_for_status()

            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Setting Next Boss: {error}")
            await asyncio.sleep(delay=3)

            return False

    async def apply_boost(self, http_client: aiohttp.ClientSession, boost_type: FreeBoostType):
        try:
            json_data = {
                'operationName': OperationName.telegramGameActivateBooster,
                'query': Query.telegramGameActivateBooster,
                'variables': {
                    'boosterType': boost_type
                }
            }

            response = await http_client.post(url=self.GRAPHQL_URL, json=json_data)
            response.raise_for_status()

            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Apply {boost_type} Boost: {error}")
            await asyncio.sleep(delay=3)

            return False

    async def upgrade_boost(self, http_client: aiohttp.ClientSession, boost_type: UpgradableBoostType):
        try:
            json_data = {
                'operationName': OperationName.telegramGamePurchaseUpgrade,
                'query': Query.telegramGamePurchaseUpgrade,
                'variables': {
                    'upgradeType': boost_type
                }
            }

            response = await http_client.post(url=self.GRAPHQL_URL, json=json_data)
            response.raise_for_status()

            return True
        except Exception:
            return False

    async def send_taps(self, http_client: aiohttp.ClientSession, nonce: str, taps: int):
        try:
            json_data = {
                'operationName': OperationName.MutationGameProcessTapsBatch,
                'query': Query.MutationGameProcessTapsBatch,
                'variables': {
                    'payload': {
                        'nonce': nonce,
                        'tapsCount': taps,
                    },
                }
            }

            response = await http_client.post(url=self.GRAPHQL_URL, json=json_data)
            response.raise_for_status()

            response_json = await response.json()
            profile_data = response_json['data']['telegramGameProcessTapsBatch']

            return profile_data
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Tapping: {error}")
            await asyncio.sleep(delay=3)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def run(self, proxy: str | None):
        access_token_created_time = 0
        turbo_time = 0
        active_turbo = False

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                try:
                    if time() - access_token_created_time >= 3600:
                        tg_web_data = await self.get_tg_web_data(proxy=proxy)
                        access_token = await self.get_access_token(http_client=http_client, tg_web_data=tg_web_data)

                        http_client.headers["Authorization"] = f"Bearer {access_token}"
                        headers["Authorization"] = f"Bearer {access_token}"

                        access_token_created_time = time()

                        profile_data = await self.get_profile_data(http_client=http_client)

                        balance = profile_data['coinsAmount']

                        nonce = profile_data['nonce']

                        current_boss = profile_data['currentBoss']
                        current_boss_level = current_boss['level']
                        boss_max_health = current_boss['maxHealth']
                        boss_current_health = current_boss['currentHealth']

                        logger.info(f"{self.session_name} | Current boss level: <m>{current_boss_level}</m> | "
                                    f"Boss health: <e>{boss_current_health}</e> out of <r>{boss_max_health}</r>")

                        await asyncio.sleep(delay=.5)

                    taps = randint(a=settings.RANDOM_TAPS_COUNT[0], b=settings.RANDOM_TAPS_COUNT[1])

                    if active_turbo:
                        taps += settings.ADD_TAPS_ON_TURBO
                        if time() - turbo_time > 10:
                            active_turbo = False
                            turbo_time = 0

                    profile_data = await self.send_taps(http_client=http_client, nonce=nonce, taps=taps)

                    if not profile_data:
                        continue

                    available_energy = profile_data['currentEnergy']
                    new_balance = profile_data['coinsAmount']
                    calc_taps = new_balance - balance
                    balance = new_balance

                    free_boosts = profile_data['freeBoosts']
                    turbo_boost_count = free_boosts['currentTurboAmount']
                    energy_boost_count = free_boosts['currentRefillEnergyAmount']

                    next_tap_level = profile_data['weaponLevel'] + 1
                    next_energy_level = profile_data['energyLimitLevel'] + 1
                    next_charge_level = profile_data['energyRechargeLevel'] + 1

                    nonce = profile_data['nonce']

                    current_boss = profile_data['currentBoss']
                    current_boss_level = current_boss['level']
                    boss_current_health = current_boss['currentHealth']

                    logger.success(f"{self.session_name} | Successful tapped! | "
                                   f"Balance: <c>{balance}</c> (<g>+{calc_taps}</g>) | "
                                   f"Boss health: <e>{boss_current_health}</e>")

                    if boss_current_health <= 0:
                        logger.info(f"{self.session_name} | Setting next boss: <m>{current_boss_level+1}</m> lvl")

                        status = await self.set_next_boss(http_client=http_client)
                        if status is True:
                            logger.success(f"{self.session_name} | Successful setting next boss: "
                                           f"<m>{current_boss_level+1}</m>")


                    if active_turbo is False:
                        if (energy_boost_count > 0
                                and available_energy < settings.MIN_AVAILABLE_ENERGY
                                and settings.APPLY_DAILY_ENERGY is True):
                            logger.info(f"{self.session_name} | Sleep 5s before activating the daily energy boost")
                            await asyncio.sleep(delay=5)

                            status = await self.apply_boost(http_client=http_client, boost_type=FreeBoostType.ENERGY)
                            if status is True:
                                logger.success(f"{self.session_name} | Energy boost applied")

                                await asyncio.sleep(delay=1)

                            continue

                        if turbo_boost_count > 0 and settings.APPLY_DAILY_TURBO is True:
                            logger.info(f"{self.session_name} | Sleep 5s before activating the daily turbo boost")
                            await asyncio.sleep(delay=5)

                            status = await self.apply_boost(http_client=http_client, boost_type=FreeBoostType.TURBO)
                            if status is True:
                                logger.success(f"{self.session_name} | Turbo boost applied")

                                await asyncio.sleep(delay=1)

                                active_turbo = True
                                turbo_time = time()

                            continue

                        if settings.AUTO_UPGRADE_TAP is True and next_tap_level <= settings.MAX_TAP_LEVEL:
                            status = await self.upgrade_boost(http_client=http_client,
                                                              boost_type=UpgradableBoostType.TAP)
                            if status is True:
                                logger.success(f"{self.session_name} | Tap upgraded to {next_tap_level} lvl")

                                await asyncio.sleep(delay=1)


                        if settings.AUTO_UPGRADE_ENERGY is True and next_energy_level <= settings.MAX_ENERGY_LEVEL:
                            status = await self.upgrade_boost(http_client=http_client,
                                                              boost_type=UpgradableBoostType.ENERGY)
                            if status is True:
                                logger.success(f"{self.session_name} | Energy upgraded to {next_energy_level} lvl")

                                await asyncio.sleep(delay=1)

                        if settings.AUTO_UPGRADE_CHARGE is True and next_charge_level <= settings.MAX_CHARGE_LEVEL:
                            status = await self.upgrade_boost(http_client=http_client,
                                                              boost_type=UpgradableBoostType.CHARGE)
                            if status is True:
                                logger.success(f"{self.session_name} | Charge upgraded to {next_charge_level} lvl")

                                await asyncio.sleep(delay=1)

                        if available_energy < settings.MIN_AVAILABLE_ENERGY:
                            logger.info(f"{self.session_name} | Minimum energy reached: {available_energy}")
                            logger.info(f"{self.session_name} | Sleep {settings.SLEEP_BY_MIN_ENERGY}s")

                            await asyncio.sleep(delay=settings.SLEEP_BY_MIN_ENERGY)

                            continue

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=3)

                else:
                    sleep_between_clicks = randint(a=settings.SLEEP_BETWEEN_TAP[0], b=settings.SLEEP_BETWEEN_TAP[1])

                    if active_turbo is True:
                        sleep_between_clicks = 4

                    logger.info(f"Sleep {sleep_between_clicks}s")
                    await asyncio.sleep(delay=sleep_between_clicks)


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
