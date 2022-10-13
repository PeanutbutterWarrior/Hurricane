import Hurricane

server = Hurricane.Server(timeout=5)

clients = []
names = {}


@server.on_new_connection
async def on_new_client(new_client: Hurricane.Client):
    clients.append(new_client)
    name = (await new_client.receive()).contents
    names[new_client] = name.title()
    print(f"{name} has joined the chat")
    for client in clients:
        if client is not new_client:
            await client.send(f"{name} has joined the chat")


@server.on_receiving_message
async def got_message(message: Hurricane.Message):
    formatted_message = f"{names[message.author]}: {message.contents}"
    print(formatted_message)
    for client in clients:
        if client is not message.author:
            await client.send(formatted_message)


@server.on_client_disconnect
async def client_left(leaving_client: Hurricane.Client):
    clients.remove(leaving_client)
    name = names.pop(leaving_client)
    print(f"{name} has left the chat")
    for client in clients:
        await client.send(f"{name} has left the chat")

server.start('localhost', 65432)
