import Hurricane

server = Hurricane.Server()


@server.on_new_connection
async def new_conn(client):
    print("connected")
    print(server._rsa_key.n)
    print(server._rsa_key.e)
    print(server._rsa_key.d)
    print(server._rsa_key.p)
    print(server._rsa_key.q)



@server.on_receiving_message
async def got_message(message):
    print("message")

server.start('localhost', 65432)