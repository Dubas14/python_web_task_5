import sys
from datetime import datetime, timedelta
import aiohttp
import asyncio
import platform
import argparse
import json
from aiofile import AIOFile, Writer
from aiopath import AsyncPath


class HttpError(Exception):
    pass


async def request(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                raise HttpError(f"Error status: {response.status} for {url}")


async def get_exchange_rates(index_day):
    d = datetime.now() - timedelta(days=int(index_day))
    shift = d.strftime("%d.%m.%Y")
    try:
        response = await request(f'https://api.privatbank.ua/p24api/exchange_rates?date={shift}')
        return response
    except HttpError as err:
        print(err)
        return None


def parse_arguments():
    parser = argparse.ArgumentParser(description="Currency exchange utility.")
    parser.add_argument('command', choices=['exchange'], help="Command to execute")
    parser.add_argument('days', type=int, help="Number of days to get exchange rates for (max 10 days)")
    return parser.parse_args()


async def log_command(result):
    """Функція для логування результату у форматі JSON"""
    log_path = AsyncPath("exchange_log.json")


    if await log_path.exists():
        async with AIOFile(log_path, 'r') as afp:
            existing_content = await afp.read()
            if existing_content:
                log_data = json.loads(existing_content)
            else:
                log_data = []
    else:
        log_data = []


    log_data.extend(result)


    async with AIOFile(log_path, 'w') as afp:
        writer = Writer(afp)
        await writer(json.dumps(log_data, indent=2))


async def main():
    args = parse_arguments()

    if args.command == 'exchange':
        days = args.days
        if days > 10:
            print("Error: You can only request exchange rates for up to 10 days.")
            return

        result = []
        for day in range(days):
            exchange_data = await get_exchange_rates(day)
            if exchange_data:
                rates = {}
                date = exchange_data['date']
                for rate in exchange_data['exchangeRate']:
                    if rate['currency'] in ['EUR', 'USD']:
                        rates[rate['currency']] = {
                            'sale': rate.get('saleRate'),
                            'purchase': rate.get('purchaseRate')
                        }
                result.append({date: rates})


        print(result)
        await log_command(result)


if __name__ == '__main__':
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
