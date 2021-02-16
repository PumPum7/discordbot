import grpc
from functions.grpc_functions import image_pb2_grpc, image_pb2


class Role:
    def __init__(self, role_id, role_name):
        self.role_id: int = role_id
        self.role_name: str = role_name


class Generator:
    @staticmethod
    async def get_level_image(exp: int, required_exp: float, position: str, user_name: str,
                              server_name: str, rank_card: str, next_role: Role, profile_picture: bytes) -> bytes:
        async with grpc.aio.insecure_channel("localhost:50051") as channel:
            stub = image_pb2_grpc.GenerateImagesStub(channel)
            response = await stub.GenerateLevelImage(
                image_pb2.LevelData(
                    EXP=exp, RequiredEXP=required_exp, Position=position, UserName=user_name, ServerName=server_name,
                    RankCard=rank_card, NextRoleName=next_role.role_name, NextRoleId=next_role.role_id,
                    profile=profile_picture,
                )
            )
        return response.Image


# TODO: write tests
# TODO: add config file here

async def main():
    generator = Generator()
    file = open("D:/Go/src/MicroServices/utils/7ad9babe7fbcd68d886e6e80f7675985.png", "rb") # read the file as bytes
    data = file.read()
    file.close()
    await generator.get_level_image(10, 100, "#12", "Pum", "Test fishy", "default",
                                    Role(role_name="test", role_id=1231), data)

if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
