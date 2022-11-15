from Hurricane.client_functions import ServerConnection
import time
import threading


def receive(server, output, expected_size):
    while len(output) != expected_size:
        message = server.recv()
        output[message.contents] = time.perf_counter_ns()


def send(server, output, num_messages, delay):
    for count in range(num_messages):
        prev_time = time.perf_counter()
        output[count] = time.perf_counter_ns()
        server.send(count)
        time.sleep(delay - time.perf_counter() + prev_time)


def run_test(num_conns, num_messages, delay):
    connections = [ServerConnection("87.75.16.230", 65432) for _ in range(num_conns)]
    send_outputs = [{} for _ in range(num_conns)]
    recv_outputs = [{} for _ in range(num_conns)]
    receiving_threads = [
        threading.Thread(
            target=receive,
            daemon=True,
            args=(connections[i], recv_outputs[i], num_messages),
        )
        for i in range(num_conns)
    ]
    sending_threads = [
        threading.Thread(
            target=send,
            daemon=True,
            args=(connections[i], send_outputs[i], num_messages, delay),
        )
        for i in range(num_conns)
    ]

    for thread in receiving_threads:
        thread.start()

    for thread in sending_threads:
        thread.start()

    for thread in sending_threads:
        thread.join()
    for thread in receiving_threads:
        thread.join()

    time_diffs = []
    for starts, ends in zip(send_outputs, recv_outputs):
        diff = {}
        for i in range(num_messages):
            diff[i] = ends[i] - starts[i]
        time_diffs.append(diff)

    averages = [sum(i.values()) / len(i) for i in time_diffs]
    return sum(averages) / len(averages)


delay = 0.1
num_messages = 50

master_conn = ServerConnection("87.75.16.230", 65432)

outputs = []
for i in range(1, 61):
    total_time = run_test(i, num_messages, delay)
    print(i, total_time / 10**9)
    outputs.append(total_time)
    message = master_conn.recv()

with open("output.txt", "w+") as file:
    for ind, item in enumerate(outputs):
        file.write(str(ind))
        file.write(" ")
        file.write(str(item))
        file.write("\n")
