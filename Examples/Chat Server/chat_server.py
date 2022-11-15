import Hurricane

server = Hurricane.Server(timeout=5)

clients = []
names = {}
containing_groups = {}

rooms = {'all': Hurricane.Group()}


@server.on_new_connection
async def on_new_client(new_client: Hurricane.Client):
    clients.append(new_client)
    rooms['all'].add(new_client)
    containing_groups[new_client] = 'all'
    name = (await new_client.receive()).contents
    names[new_client] = name.title()
    print(f"{name} has joined the chat")
    await rooms['all'].send(f"{name} has joined the chat")


@server.on_receiving_message
async def got_message(message: Hurricane.Message):
    if message.contents[:6] == "/join ":
        group_name = message.contents[6:]
        if group_name not in rooms:
            rooms[group_name] = Hurricane.Group()
        old_group_name = containing_groups[message.author]

        rooms[old_group_name].remove(message.author)

        await rooms[old_group_name].send(f"{names[message.author]} has changed to group {group_name}")
        await rooms[group_name].send(f"{names[message.author]} has joined group {group_name}")
        await message.author.send(f"You have changed to group {group_name}")

        rooms[group_name].add(message.author)
        containing_groups[message.author] = group_name
        print(f"{names[message.author]} changed from group {old_group_name} to {group_name}")
    else:
        formatted_message = f"{names[message.author]}: {message.contents}"
        print(formatted_message)
        group_name = containing_groups[message.author]
        await rooms[group_name].send(formatted_message)


@server.on_client_disconnect
async def client_left(leaving_client: Hurricane.Client):
    clients.remove(leaving_client)
    name = names.pop(leaving_client)
    print(f"{name} has left the chat")
    for client in clients:
        await client.send(f"{name} has left the chat")

server.start('0.0.0.0', 65432)
