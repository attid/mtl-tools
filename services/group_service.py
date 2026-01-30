from typing import List, Protocol
from other.pyro_tools import get_group_members, remove_deleted_users, GroupMember

class IGroupService(Protocol):
    async def get_members(self, chat_id: int) -> List[GroupMember]:
        ...
    
    async def remove_deleted_users(self, chat_id: int) -> int:
        ...

class GroupService:
    async def get_members(self, chat_id: int) -> List[GroupMember]:
        return await get_group_members(chat_id)
        
    async def remove_deleted_users(self, chat_id: int) -> int:
        return await remove_deleted_users(chat_id)

    async def ping_piro(self):
        from other.pyro_tools import pyro_test
        await pyro_test()
