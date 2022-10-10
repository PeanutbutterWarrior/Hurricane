from Hurricane import server
from Hurricane.message import Message

from pprint import pprint
import time

server = server.Server(timeout=5)


@server.on_new_connection
async def new_client(client):
    print(f"New client connected with id {client.uuid}")


@server.on_receiving_message
async def got_message(data: Message):
    print(f"Received {data.contents} from {data.author.uuid}")

    if data.contents == "clients":
        pprint(server._clients)
    elif data.contents == "error":
        _ = ([1, 2, 3])[3]
    elif data.contents == "sleep":
        print("Sleeping")
        time.sleep(5)
        print("Awake")

    await data.author.send(f"Got first part")

    second = await data.author.receive()
    await data.author.send(f"Concat: {data.contents + second.contents}")


@server.on_client_disconnect
async def client_disconnect(client):
    print(f"Client {client.uuid} disconnected")


@server.on_client_reconnect
async def client_reconnect(client):
    print(f"Client {client.uuid} reconnected")


server.start("0.0.0.0", 65432)
