import asyncio

async def gen():
    await asyncio.sleep(0.1)
    yield 42

generator = gen()
print(generator)

async def main():
    print(await anext(generator))

asyncio.run(main())