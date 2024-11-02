import asyncio

from utils.grist_tools import load_notify_sp_chats, load_notify_sp_users
from utils.pyro_tools import get_group_members, pyro_app


async def check_user_in_chats():
    chats = await load_notify_sp_chats()
    all_users = await load_notify_sp_users()
    users = [user for user in all_users if not user['DISABLED']]
    alerts = []

    user_ids = [user['TELEGRAM_ID'] for user in users]

    for chat in chats:
        members = await get_group_members(chat['TELEGRAM_ID'])
        member_ids = [member.user_id for member in members if not member.is_bot]

        if chat['REQUIRED']:
            # Check if all users are in the required chat
            for user_id in user_ids:
                if user_id not in member_ids:
                    user = next((u for u in users if u['TELEGRAM_ID'] == user_id), None)
                    username = user['USERNAME'] if user else 'Unknown'
                    alerts.append(f"Need Add User @{username} (ID: {user_id}) in chat: {chat['NAME']}")

            # Check if there are any unexpected members in the required chat
            for member_id in member_ids:
                if member_id not in user_ids:
                    member = next((m for m in members if m.user_id == member_id), None)
                    username = member.username if member else 'Unknown'
                    alerts.append(f"Need Remove User @{username} (ID: {member_id}) from chat {chat['NAME']}")
        else:
            # Check if there are any unexpected members in the required chat
            for member_id in member_ids:
                if member_id not in user_ids:
                    member = next((m for m in members if m.user_id == member_id), None)
                    username = member.username if member else 'Unknown'
                    alerts.append(f"Need Remove User @{username} (ID: {member_id}) from chat {chat['NAME']}")

    return alerts


async def main():
    await pyro_app.start()

    a = await check_user_in_chats()
    print(a)
    try:
        await pyro_app.stop()
    except Exception as e:
        pass


if __name__ == '__main__':
    asyncio.run(main())
