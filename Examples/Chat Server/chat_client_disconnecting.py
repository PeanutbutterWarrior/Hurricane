from Hurricane.client_functions import ServerConnection
import socket
import tkinter as tk
import threading
import time


def send_message():
    server.send(entry_box.get())
    entry_box.delete(0, "end")


def receive_message():
    while True:
        try:
            message = server.recv()
        except OSError:
            continue
        text_box["state"] = "normal"
        text_box.insert("end", "\n" + message.contents)
        text_box["state"] = "disabled"


def reset_connection():
    server.socket.shutdown(2)
    server.socket.close()


window = tk.Tk()
text_box = tk.Text(width=50, height=20, state="disabled")
entry_box = tk.Entry(width=40)
submit = tk.Button(text="Submit", width=10, command=send_message)
reconnect = tk.Button(text="Reconnect", command=reset_connection)

text_box.pack()
entry_box.pack()
submit.pack()
reconnect.pack()

receiving_thread = threading.Thread(target=receive_message, daemon=True)

with ServerConnection("localhost", 65432, socket.AF_INET, socket.SOCK_STREAM) as server:
    name = input("Name: ")
    server.send(name)
    receiving_thread.start()
    window.mainloop()
