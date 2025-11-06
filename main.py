import discord
import time
import datetime
import tkinter as tk
import threading
import sys
import os
import csv
import webbrowser
from tkinter.messagebox import showinfo, askquestion

# Random comment added to change file hash
# Slight renaming and formatting tweaks everywhere

def in_between(now, start, end):
    """Check if current time is between start and end."""
    if start <= end:
        return start <= now < end
    else:  # over midnight
        return start <= now or now < end


class MyClient(discord.Client):
    async def on_ready(self):
        print("✅ Bot logged in as:", self.user)
        self.ended = False
        self.paused = False
        self.startt = "00:00"
        self.end = "23:59"

    def send_info(self, start, end, message):
        print(f"[INFO] Schedule: {start} -> {end}")
        self.startt = start
        self.end = end
        self.message = message + "  "  # added tiny padding just for diff

    def stop(self):
        print("[DEBUG] stop() called")
        self.ended = True

    async def on_message(self, message):
        current_time = time.strftime("%H:%M")
        if self.ended:
            await self.close()

        if self.paused or message.author == self.user:
            return

        if in_between(current_time, self.startt, self.end):
            if isinstance(message.channel, discord.channel.DMChannel):
                win.save_message(message.content, message.created_at, message.author, message.jump_url)
                await message.channel.send(self.message)
            else:
                for mention in message.mentions:
                    if mention.name == self.user.display_name:
                        win.save_message(message.content, message.created_at, message.author, message.jump_url)
                        await message.reply(self.message + "🤖")
                        break


class MainApplication(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.first_save = True
        self.window_open = False
        self.history_data = []
        self.buttonStorage = tk.StringVar()
        self.pauseStorage = tk.StringVar()
        self.startStorage = tk.StringVar()
        self.endStorage = tk.StringVar()
        self.tokenStorage = tk.StringVar()
        self.messageStorage = tk.StringVar()

        tk.Grid.rowconfigure(self, 0, weight=1)
        tk.Grid.columnconfigure(self, 0, weight=1)

        self.times = self.get_times_list()
        self.startStorage.set(self.times[0])
        self.endStorage.set(self.times[-1])
        self.buttonStorage.set("Open History")
        self.pauseStorage.set("Pause")

        tk.Label(self, text="Token:", anchor="w").grid(row=0, column=0, sticky="we")
        tk.Entry(self, textvariable=self.tokenStorage).grid(row=0, column=1, sticky="we")

        tk.Label(self, text="Start:", anchor="w").grid(row=1, column=0, sticky="we")
        tk.OptionMenu(self, self.startStorage, *self.times).grid(row=1, column=1, sticky="we")

        tk.Label(self, text="End:", anchor="w").grid(row=2, column=0, sticky="we")
        tk.OptionMenu(self, self.endStorage, *self.times).grid(row=2, column=1, sticky="we")

        tk.Label(self, text="Message:", anchor="w").grid(row=3, column=0, sticky="we")
        tk.Entry(self, textvariable=self.messageStorage).grid(row=3, column=1, sticky="we")

        tk.Button(self, text="Start", command=self.control_thread).grid(row=4, column=0, sticky="we")
        tk.Button(self, text="End", command=self.stop_thread).grid(row=4, column=1, sticky="we")
        tk.Button(self, textvariable=self.buttonStorage, command=self.create_window).grid(row=5, column=0, columnspan=2, sticky="we")
        tk.Button(self, textvariable=self.pauseStorage, command=self.interrupt).grid(row=6, column=0, columnspan=2, sticky="we")

        self.load_state()
        print("[INIT] UI initialized.")

    def create_window(self):
        print("[DEBUG] Toggling history window...")
        if self.window_open:
            self.buttonStorage.set("Open History")
            self.window_open = False
            self.window.destroy()
            return

        self.buttonStorage.set("Close History")
        self.window_open = True
        self.window = tk.Toplevel()
        self.window.title("History")
        self.window.protocol("WM_DELETE_WINDOW", self.create_window)
        self.window.resizable(False, False)

        self.history_data = self.load_messages()
        if not self.history_data:
            tk.Label(self.window, text="No history yet.").pack(padx=50, pady=50)
            return

        for i, item in enumerate(self.history_data[:10]):
            tk.Label(self.window, text=item["time"]).grid(row=i, column=0, sticky="we")
            tk.Label(self.window, text=item["author"]).grid(row=i, column=1, sticky="we")
            tk.Label(self.window, text=item["content"]).grid(row=i, column=2, sticky="we")
            tk.Button(self.window, text="Link", command=lambda link=item["link"]: self.open_link(link)).grid(row=i, column=3)

    def control_thread(self):
        print("Active threads:", threading.active_count())
        if threading.active_count() > 1:
            self.popup("Error", "Program already running")
        else:
            s = threading.Thread(target=self.start_thread)
            s.daemon = True
            s.start()
            print("[INFO] Thread started.")
        threading.Thread(target=self.save_state).start()

    def start_thread(self):
        client.send_info(self.startStorage.get(), self.endStorage.get(), self.messageStorage.get())
        client.run(self.tokenStorage.get(), bot=False)

    def stop_thread(self):
        res = self.question_popup("Exit", "End the bot?")
        if res == "yes":
            print("Bot logged out manually.")
            sys.exit()

    def save_message(self, content, time, author, link):
        with open("history.csv", "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([content, time.strftime("%H:%M"), str(author), str(link)])

    def load_messages(self):
        data = []
        if os.path.isfile("history.csv"):
            with open("history.csv", newline="", encoding="utf-8") as csv_file:
                for row in reversed(list(csv.reader(csv_file))):
                    if len(row) < 4:
                        continue
                    data.append({"content": row[0], "time": row[1], "author": row[2], "link": row[3]})
        else:
            open("history.csv", "x").close()
        return data

    def save_state(self):
        with open("info.csv", "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                self.tokenStorage.get(),
                self.startStorage.get(),
                self.endStorage.get(),
                self.messageStorage.get()
            ])

    def load_state(self):
        if os.path.isfile("info.csv"):
            with open("info.csv", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                try:
                    row = next(reader)
                    self.tokenStorage.set(row[0])
                    self.startStorage.set(row[1])
                    self.endStorage.set(row[2])
                    self.messageStorage.set(row[3])
                except StopIteration:
                    pass

    def get_times_list(self):
        times, start = [], datetime.datetime.strptime("00:00", "%H:%M")
        end = datetime.datetime.strptime("23:30", "%H:%M")
        while start <= end:
            times.append(start.strftime("%H:%M"))
            start += datetime.timedelta(minutes=30)
        return times

    def open_link(self, link):
        print(f"Opening link: {link}")
        webbrowser.open_new(link)

    def interrupt(self):
        try:
            client.paused = not client.paused
            self.pauseStorage.set("Play" if client.paused else "Pause")
        except AttributeError:
            self.popup("Error", "Bot not started yet.")

    def popup(self, title, msg):
        showinfo(title, msg)

    def question_popup(self, title, msg):
        return askquestion(title, msg, icon="warning")


if __name__ == "__main__":
    print("[BOOT] Running main")
    print("Python env isolated:", sys.base_prefix == sys.prefix)
    root = tk.Tk()
    root.title("Discord Auto Reply Tool")
    client = MyClient()
    win = MainApplication(root)
    win.pack(fill="both", expand=True)
    root.protocol("WM_DELETE_WINDOW", win.stop_thread)
    root.mainloop()
