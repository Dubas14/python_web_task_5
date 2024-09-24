import asyncio
from datetime import datetime
import websockets
from aiofile import AIOFile, Writer
from aiopath import AsyncPath
from currency_util import get_exchange_rates

class ChatServer:
    clients = set()

    async def register(self, websocket):
        self.clients.add(websocket)
        await self.notify_clients(f"New user joined: {len(self.clients)} users connected")

    async def unregister(self, websocket):
        self.clients.remove(websocket)
        await self.notify_clients(f"User left: {len(self.clients)} users remaining")

    async def notify_clients(self, message):
        if self.clients:
            await asyncio.wait([client.send(message) for client in self.clients])

    async def handle_message(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                if message.startswith("exchange"):
                    cmd_parts = message.split()
                    days = int(cmd_parts[1]) if len(cmd_parts) > 1 else 1
                    currencies = cmd_parts[2:] if len(cmd_parts) > 2 else ['EUR', 'USD']
                    rates = await get_exchange_rates(days, currencies)
                    response = "\n".join([f"{day}: {rates}" for day in rates])
                    await self.notify_clients(response)
                    await log_command(message)
                else:
                    await self.notify_clients(f"Received message: {message}")
        finally:
            await self.unregister(websocket)

async def log_command(command):
    log_file = AsyncPath('exchange_log.txt')
    async with AIOFile(log_file, 'a') as afp:
        writer = Writer(afp)
        await writer(f"Command executed: {command} at {datetime.now()}\n")

if __name__ == "__main__":
    chat_server = ChatServer()
    start_server = websockets.serve(chat_server.handle_message, "localhost", 12345)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
