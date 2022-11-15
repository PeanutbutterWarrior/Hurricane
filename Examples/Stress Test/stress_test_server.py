import Hurricane

server = Hurricane.Server(timeout=1)

master_conn: Hurricane.Client | None = None


@server.on_new_connection
async def new_conn(client):
    global master_conn
    if master_conn is None:
        master_conn = client


@server.on_client_disconnect
async def disconnect(client):
    if len(server._clients) == 1:
        await master_conn.send(0)


@server.on_receiving_message
async def got_mail(message: Hurricane.Message):
    await message.author.send(message.contents)


server.start("0.0.0.0", 65432)
