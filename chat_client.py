from Hurricane.client_functions import ServerConnection
import socket
import tkinter as tk
import threading


def send_message():
    server.send(entry_box.get())
    entry_box.delete(0, 'end')


def receive_message():
    while True:
        message = server.recv()
        print(f"got message {message[0]}")
        text_box['state'] = 'normal'
        text_box.insert('end', '\n' + message[0])
        text_box['state'] = 'disabled'


window = tk.Tk()
text_box = tk.Text(width=50, height=20, state='disabled')
entry_box = tk.Entry(width=40)
submit = tk.Button(text="Submit", width=10, command=send_message)

text_box.pack()
entry_box.pack()
submit.pack()

receiving_thread = threading.Thread(target=receive_message, daemon=True)

with ServerConnection('localhost', 65432, socket.AF_INET, socket.SOCK_STREAM) as server:
    name = input("Name: ")
    server.send(name)
    receiving_thread.start()
    window.mainloop()
