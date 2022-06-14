from typing import List

import asyncio


# Used to keep a reference to any tasks
# asyncio.create_task only creates a weak reference to the task
# If no other reference is kept, the garbage collector can destroy it before the task runs
# A callback to discard() should be used to remove the task once it has finished running
# See https://docs.python.org/3/library/asyncio-task.html#creating-tasks
task_references = set()


class Server:
    def __init__(self):
        self._clients: List[Client] = []
        self._new_connection_callback = None
        self._recieved_message_callback = None

    def __new_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        new_client = Client(reader, writer, None, None)
        self._clients.append(new_client)
        if self._new_connection_callback:
            task = asyncio.create_task(self._new_connection_callback(new_client)).add_done_callback(task_references.discard)
            task_references.add(task)
        task = asyncio.create_task(new_client._wait_for_read(self._recieved_message_callback)).add_done_callback(task_references.discard)
        task_references.add(task)

    def start(self):
        async def runner():
            server = await asyncio.start_server(self.__new_client, host='127.0.0.1', port=65432)
            async with server:
                await server.serve_forever()

        asyncio.run(runner())

    def on_new_connection(self, coro):
        self._new_connection_callback = coro
        return coro
    
    def on_recieving_message(self, coro):
        self._recieved_message_callback = coro
        return coro


class Client:
    def __init__(self,
                 tcp_reader: asyncio.StreamReader,
                 tcp_writer: asyncio.StreamWriter,
                 udp_reader: asyncio.StreamReader,
                 udp_writer: asyncio.StreamWriter):

        self.__tcp_reader: asyncio.StreamReader = tcp_reader
        self.__tcp_writer: asyncio.StreamWriter = tcp_writer
    
    async def _wait_for_read(self, callback):
        header = b''
        while len(header) < 4:
            header = header + await self.__tcp_reader.read(4 - len(header))
        message_size = int.from_bytes(header, 'big') # Big endian

        data = b''
        while len(data) < message_size:
            data = data + await self.__tcp_reader.read(message_size - len(data))
        
        asyncio.create_task(callback(data))
        

    async def send(self, data: bytes):
        self.__tcp_writer.write(data)
        await self.__tcp_writer.drain()


class Message:
    ...


class Group:
    ...
