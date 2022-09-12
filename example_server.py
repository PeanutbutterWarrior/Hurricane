from Hurricane import server
from Hurricane.message import Message

server = server.Server()

names= {}


@server.on_new_connection
async def new_client(client):
    print("New client connected")


@server.on_receiving_message
async def got_message(data: Message):
    print(f"Received {data.contents} from {names[data.author]}")
    if data.author not in names:
        names[data.author] = data.contents
    else:
        await data.author.send(f"Received {data.contents} successfully")


@server.on_client_disconnect
async def client_disconnect(client):
    print("Client disconnected")

server.start("0.0.0.0", 65432)
