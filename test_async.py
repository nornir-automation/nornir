import asyncio
import os
from nornir import InitNornir

os.chdir("docs/tutorial")


async def my_coroutine(host, text):
    print(f"begining {host}")
    print(text)
    await asyncio.sleep(1)
    print(f"end {host}")


nr = InitNornir(config_file="config.yaml")

asyncio.run(nr.run_async(my_coroutine, text="hello world"))
