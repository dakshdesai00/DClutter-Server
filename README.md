DClutter Server V-1

DClutter server offers an alternative to Samba for remote file sharing via HTTP. While Samba is effective in many scenarios, it may not be optimal for slower servers like those based on Raspberry Pi connected to low-speed networks. Unlike Samba, which downloads and displays files when opening a folder, DClutter enables faster file navigation by displaying file lists without necessarily downloading all files upfront. This approach enhances efficiency in accessing and managing files over such network conditions.

---

Installation:

- Install [redis-stack-server](https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/) and start redis server

- Install [Python](https://www.python.org/downloads/)

- Clone this Github repo

- Install packages from requirements.txt using `pip install requirements.txt`

- Create a .env file in the same directory as main.py file and configure it with these entries

```python
MaxSizeInMemory = 2 #This is max size of file buffer stored in ram keep this as 1-2 if you have low memory in your server

SecretKey = "A RANDOM STRING" #Put a random string here which will be used for JWT hashing

DBPORT = 6379 # This is default port for redis-stack-server but you can use a diffrent port to server your redis database
```

- Now start server using `python main.py`

---

Endpoints availabe can be seen on running server at `/docs` endpoint.

---

New features like auto encrypted backup on telegram is being worked on
