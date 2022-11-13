from Hurricane.queue import Queue
import pytest
import asyncio


@pytest.fixture
def runner():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def test_simple_queue():
    q = Queue()
    q.push(1)
    q.push(2)
    assert q.pop() == 1
    assert q.pop() == 2
    assert len(q) == 0


def test_long_queue():
    q = Queue()
    for i in range(10000):
        q.push(i)
    for j in range(10000):
        assert q.pop() == j

    assert len(q) == 0


def test_empty_pop():
    q = Queue()
    with pytest.raises(IndexError):
        q.pop()
    q.push(2)
    q.pop()
    with pytest.raises(IndexError):
        q.pop()


def test_async_pop(runner):
    q = Queue()
    q.push(2)
    q.push(4)

    assert runner.run_until_complete(q.async_pop()) == 2
    assert runner.run_until_complete(q.async_pop()) == 4


def test_empty_async_pop(runner):
    q = Queue()

    with pytest.raises(asyncio.TimeoutError):
        runner.run_until_complete(asyncio.wait_for(q.async_pop(), 0.1))

    q.push(1)
    runner.run_until_complete(q.async_pop())
    with pytest.raises(asyncio.TimeoutError):
        runner.run_until_complete(asyncio.wait_for(q.async_pop(), 0.1))


def test_pop_then_async_pop(runner):
    q = Queue()
    q.push(1)
    q.push(2)

    q.pop()
    assert runner.run_until_complete(q.async_pop()) == 2


def test_async_pop_then_pop(runner):
    q = Queue()
    q.push(1)
    q.push(2)

    runner.run_until_complete(q.async_pop())
    assert q.pop() == 2


def test_pop_then_async_pop_empty(runner):
    q = Queue()
    q.push(1)

    q.pop()

    with pytest.raises(asyncio.TimeoutError):
        runner.run_until_complete(asyncio.wait_for(q.async_pop(), 0.1))


def test_async_pop_then_empty_pop(runner):
    q = Queue()
    q.push(1)

    runner.run_until_complete(q.async_pop())
    with pytest.raises(IndexError):
        q.pop()


def test_async_pop_then_push(runner):
    q = Queue()

    async def inner():
        t = asyncio.create_task(q.async_pop())
        await asyncio.sleep(0)  # Yield execution to run other tasks
        q.push(3)
        return await t

    assert runner.run_until_complete(inner()) == 3
