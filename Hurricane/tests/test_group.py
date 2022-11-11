from Hurricane.group import Group
import asyncio


class PatchedClient:
    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)


def test_simple():
    group = Group()
    clients = [PatchedClient() for _ in range(5)]

    for client in clients:
        group.add(client)
    asyncio.run(group.send("a"))

    for client in clients:
        assert client.sent_messages == ["a"]


def test_removing():
    group = Group()
    client_1 = PatchedClient()
    client_2 = PatchedClient()
    group.add(client_1)
    group.add(client_2)

    asyncio.run(group.send("a"))
    group.remove(client_1)
    asyncio.run(group.send("b"))

    assert client_1.sent_messages == ["a"]
    assert client_2.sent_messages == ["a", "b"]


def test_nested():
    parent_group = Group()
    child_group = Group()
    client = PatchedClient()
    parent_group.add(child_group)
    child_group.add(client)

    asyncio.run(parent_group.send("b"))
    assert client.sent_messages == ["b"]


def test_deeply_nested():
    top_level_group = Group()
    previous_group = top_level_group
    groups = []

    for _ in range(100):
        new_group = Group()
        groups.append(new_group)
        previous_group.add(new_group)
        previous_group = new_group

    client = PatchedClient()
    previous_group.add(client)

    asyncio.run(top_level_group.send("c"))
    assert client.sent_messages == ["c"]


def test_recursive():
    group_1 = Group()
    group_2 = Group()
    client = PatchedClient()
    group_1.add(group_2)
    group_2.add(group_1)
    group_2.add(client)

    asyncio.run(group_1.send("a"))
    asyncio.run(group_2.send("b"))

    assert client.sent_messages == ["a", "b"]

    group_1.add(client)
    asyncio.run(group_1.send("c"))
    assert client.sent_messages == ["a", "b", "c"]
