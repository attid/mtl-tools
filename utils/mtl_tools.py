import asyncio
from aiogram import Bot
from utils.config_reader import config
from utils.grist_tools import load_notify_sp_chats, load_notify_sp_users, load_mtla_chats, load_mtla_councils
from utils.pyro_tools import get_group_members, pyro_app


async def check_user_in_sp_chats():
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


async def check_consul_mtla_chats(bot: Bot):
    # Смотрим пример в check_user_in_sp_chats
    # вызываем load_mtla_chats получим -
    # [{'TELEGRAM_ID': -1001998432893, 'TITLE': '2\xa0MTLAP Club', 'NEED_SET_COUNCIL_TITLE': True}, {'TELEGRAM_ID': -1002446981251, 'TITLE': '1\xa0MTLAP Club', 'NEED_SET_COUNCIL_TITLE': True}, {'TELEGRAM_ID': -1002034958562, 'TITLE': '3\xa0MTLAP Club', 'NEED_SET_COUNCIL_TITLE': True}, {'TELEGRAM_ID': -1002013470654, 'TITLE': '4\xa0MTLAP Club', 'NEED_SET_COUNCIL_TITLE': True}, {'TELEGRAM_ID': -1002380723477, 'TITLE': '5\xa0MTLAP Club', 'NEED_SET_COUNCIL_TITLE': True}, {'TELEGRAM_ID': -1001892843127, 'TITLE': 'MTLA: Assembly | Собрание Ассоциации', 'NEED_SET_COUNCIL_TITLE': True}]
    # потом вызываем
    # # load_mtla_councils получим
    # # [{'TELEGRAM_ID': 84131737, 'USERNAME': 'itolstov', 'STELLAR': 'GDLTH4KKMA4R2JGKA7XKI5DLHJBUT42D5RHVK6SS6YHZZLHVLCWJAYXI', 'EMAIL': 'attid0@gmail.com', 'DISABLED': False, 'WEIGHT': 0, 'CHAT_TITLE': 'Council'},
    # для каждого чата вызываем get_group_members
    # потом надо сделать 3 шага для каждого чата
    # 1 - проверить что все советы есть в чате, если нет то пишем сообщение что не нашли такого
    # 2 - смотрим чтоб админы были в списке консулов, если кто-то админ не консул пробуем отобрать права если не выходит то ругаемся.
    # 3 - если консул не админ в чате то делаем админом,с правом только пинить, и даем титл который пописан. 'CHAT_TITLE': 'Council'
    # вот пример команд для тутла и становления админом
    # await bot.promote_chat_member(chat_id=message.chat.id,
    #                                       user_id=3718221,
    #                                       can_pin_messages=True)
    # await bot.set_chat_administrator_custom_title(chat_id=message.chat.id,
    #                                                       user_id=3718221,
    #                                                       custom_title="мой кожаный")
    chats = await load_mtla_chats()
    councils = await load_mtla_councils()
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
                alerts.append(f"Council member @{council['USERNAME']} "
                              f"(ID: {council['TELEGRAM_ID']}) not found in chat: {chat['TITLE']}")

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
        a = await check_consul_mtla_chats(bot)
        print('\n'.join(a))

    try:
        await pyro_app.stop()
    except Exception as e:
        pass


if __name__ == '__main__':
    asyncio.run(main())
