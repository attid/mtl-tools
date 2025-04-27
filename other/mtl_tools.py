import asyncio
from aiogram import Bot
from other.config_reader import config
from other.grist_tools import MTLGrist, grist_manager
from other.pyro_tools import get_group_members, pyro_app


async def check_user_in_sp_chats(bot: Bot, need_remove: bool = False):
    chats = await grist_manager.load_table_data(MTLGrist.SP_CHATS)
    all_users = await grist_manager.load_table_data(MTLGrist.SP_USERS)
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
                    alerts.append(f"Need Add User @{username} (ID: {user_id}) in chat: {chat['TITLE']}")

            # Check if there are any unexpected members in the required chat
            for member_id in member_ids:
                if member_id not in user_ids:
                    member = next((m for m in members if m.user_id == member_id), None)
                    username = member.username if member else 'Unknown'
                    alerts.append(f"Need Remove User @{username} (ID: {member_id}) from chat {chat['TITLE']}")
                    if need_remove:
                        try:
                            await bot.unban_chat_member(chat_id=chat['TELEGRAM_ID'], user_id=member_id)
                        except Exception as e:
                            alerts.append(f"Error removing user @{username} (ID: {member_id}) from chat {chat['TITLE']}: {str(e)}")
        else:
            # Check if there are any unexpected members in the required chat
            for member_id in member_ids:
                if member_id not in user_ids:
                    member = next((m for m in members if m.user_id == member_id), None)
                    username = member.username if member else 'Unknown'
                    alerts.append(f"Need Remove User @{username} (ID: {member_id}) from chat {chat['TITLE']}")
                    try:
                        await bot.unban_chat_member(chat_id=chat['TELEGRAM_ID'], user_id=member_id)
                    except Exception as e:
                        alerts.append(f"Error removing user @{username} (ID: {member_id}) from chat {chat['TITLE']}: {str(e)}")

    return alerts


async def check_consul_mtla_chats(bot: Bot):
    chats = await grist_manager.load_table_data(MTLGrist.MTLA_CHATS)
    councils = await grist_manager.load_table_data(MTLGrist.MTLA_COUNCILS)
    alerts = []
    councils = [council for council in councils if not council['DISABLED']]


    for chat in chats:
        await asyncio.sleep(1)
        members = await get_group_members(chat['TELEGRAM_ID'])
        members = [member for member in members if not member.is_bot]
        member_ids = [member.user_id for member in members]
        admins = [member for member in members if member.is_admin]
        admin_ids = [admin.user_id for admin in admins]

        # Step 1: Check if all council members are in the chat
        for council in councils:
            if council['TELEGRAM_ID'] not in member_ids:
                pass
                # alerts.append(f"Council member @{council['USERNAME']} "
                #              f"(ID: {council['TELEGRAM_ID']}) not found in chat: {chat['TITLE']}")

        # Step 2: Check if admins are council members
        for admin in admins:
            if admin.user_id not in [c['TELEGRAM_ID'] for c in councils]:
                try:
                    await bot.promote_chat_member(chat_id=chat['TELEGRAM_ID'], user_id=admin.user_id,
                                                  is_anonymous=False)
                    alerts.append(f"Revoked admin rights from non-council member "
                                  f"@{admin.username} (ID: {admin.user_id}) in chat: {chat['TITLE']}")
                    await asyncio.sleep(1)
                except Exception as e:
                    alerts.append(f"Failed to revoke admin rights from non-council member "
                                  f"@{admin.username} (ID: {admin.user_id}) in chat: {chat['TITLE']}. Error: {str(e)}")

        # Step 3: Make council members admins with correct title
        for council in councils:
            if council['TELEGRAM_ID'] not in admin_ids:
                try:
                    if chat['NEED_SET_COUNCIL_TITLE'] and council['TELEGRAM_ID'] in member_ids:
                        await bot.promote_chat_member(chat_id=chat['TELEGRAM_ID'], user_id=council['TELEGRAM_ID'],
                                                      can_pin_messages=True)
                        await bot.set_chat_administrator_custom_title(chat_id=chat['TELEGRAM_ID'],
                                                                      user_id=council['TELEGRAM_ID'],
                                                                      custom_title=council['CHAT_TITLE'])
                        alerts.append(f"Made council member @{council['USERNAME']} "
                                      f"(ID: {council['TELEGRAM_ID']}) admin in chat: {chat['TITLE']}")
                        await asyncio.sleep(2)
                except Exception as e:
                    alerts.append(f"Failed to make council member @{council['USERNAME']} "
                                  f"(ID: {council['TELEGRAM_ID']}) admin in chat: {chat['TITLE']}. Error: {str(e)}")

    return alerts


async def main():
    await pyro_app.start()

    async with Bot(
            token=config.bot_token.get_secret_value(),
    ) as bot:
        # a = await check_user_in_sp_chats()
        a = await check_user_in_sp_chats(bot, True)
        print('\n'.join(a))

    try:
        await pyro_app.stop()
    except Exception:
        pass


if __name__ == '__main__':
    asyncio.run(main())
