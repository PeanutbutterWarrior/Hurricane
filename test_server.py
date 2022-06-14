import asyncio

import Server

server = Server.Server()

@server.on_new_connection
async def new_client(client):
    print("New client connected")

@server.on_recieving_message
async def got_message(data):
    print(f"Recieved {data}")

server.start()