import aiohttp


async def get_profile_bytes(avatar_url: str):
    # gets the avatar image as bytes
    async with aiohttp.ClientSession() as session:
        async with session.get(url=avatar_url) as result:
            if result.status != 200:
                return result.raise_for_status()
            else:
                image = await result.read()
    return image
