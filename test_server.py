import Server
from Message import Message

server = Server.Server()


@server.on_new_connection
async def new_client(client):
    print("New client connected")


@server.on_receiving_message
async def got_message(data: Message):
    print(f"Received {data.contents}")
    await data.author.send(input("Reply: ").encode("utf-8"))

server.start("0.0.0.0", 65432)
