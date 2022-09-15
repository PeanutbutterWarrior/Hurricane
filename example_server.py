from Hurricane import server
from Hurricane.message import Message

from pprint import pprint

server = server.Server(5)

names = {}


@server.on_new_connection
async def new_client(client):
    print(f"New client connected with id {client.uuid}")


@server.on_receiving_message
async def got_message(data: Message):
    if data.author not in names:
        names[data.author] = data.contents
    await data.author.send(f"Received {data.contents} successfully")

    if data.contents == "clients":
        pprint(server._clients)
    print(f"Received {data.contents} from {names[data.author]}")


@server.on_client_disconnect
async def client_disconnect(client):
    print("Client disconnected")


@server.on_client_reconnect
async def client_reconnect(client):
    print("Client reconnected")

server.start("0.0.0.0", 65432)
