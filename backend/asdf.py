import asyncio
import httpx

async def testing():
    client = httpx.AsyncClient()
    response = await client.get("https://www.google.com/")
    await client.aclose()
    print(response.status_code)

async def main():
   await testing()

asyncio.run(main())
