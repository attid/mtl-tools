from aiogram import Router, Bot, F
import re # Add re import for regex operations
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReactionTypeEmoji
from loguru import logger
from sqlalchemy.orm import Session

from db.repositories import ChatsRepository
from other.constants import MTLChats
from services.command_registry_service import update_command_info
from other.stellar import MTLAddresses

router = Router()

startmsg = """
Привет, я бот из <a href="https://montelibero.org">Монтелиберо</a>.
Помогаю справляться с задачами, либо просто можем пообщаться.
Чтобы увидеть все, что я умею, наберите в поле ввода @mymtlbot и любое слово для поиска команды
"""

link_stellar = "https://viewer.eurmtl.me/account/"
link_json = "https://raw.githubusercontent.com/montelibero-org/mtl/main/json/"

links_msg = f"""
Полезные ссылки

[Отчет по фонду](https://docs.google.com/spreadsheets/d/1fTOWq7JqX24YEqhCZTQ-z8IICPpgBHXcj91moxkT6R4/edit#gid=1372993507)
[Список всех документов](https://docs.google.com/spreadsheets/d/1x3E1ai_kPVMQ85nuGwuTq1bXD051fnVlf0Dz9NaFoq0)
Тулзы [для подписания](mtl.ergvein.net/) / [расчет голосов и дивов](https://ncrashed.github.io/dividend-tools/votes/)
[Лаборатория](https://laboratory.stellar.org/#?network=public)
Ссылки на аккаунты фонда / [Эмитент]({link_stellar}{MTLAddresses.public_issuer}) /  [Залоговый счет]({link_stellar}{MTLAddresses.public_pawnshop})
Стакан на [мульки](https://stellar.expert/explorer/public/market/EURMTL-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V/XLM) [mtl](https://stellar.expert/explorer/public/market/EURMTL-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V/MTL-GACKTN5DAZGWXRWB2WLM6OPBDHAMT6SJNGLJZPQMEZBUR4JUGBX2UK7V)
Списки [черный]({link_json}blacklist.json) / [BL for DG]({link_json}dg_blacklist.json) 
Боты [Обмен eurmtl_xlm]({link_stellar}{MTLAddresses.public_exchange_eurmtl_xlm}) / \
[Обмен eurmtl_usdc]({link_stellar}{MTLAddresses.public_exchange_eurmtl_usdm}) / \
[Обмен usdm_sats]({link_stellar}{MTLAddresses.public_exchange_usdm_sats}) / \
[Обмен usdm_mtlfarm]({link_stellar}{MTLAddresses.public_exchange_usdm_mtlfarm}) / \
[Дивиденды]({link_stellar}GDNHQWZRZDZZBARNOH6VFFXMN6LBUNZTZHOKBUT7GREOWBTZI4FGS7IQ/) / \
[BIM-XLM]({link_stellar}GARUNHJH3U5LCO573JSZU4IOBEVQL6OJAAPISN4JKBG2IYUGLLVPX5OH) / \
[BIM-EURMTL]({link_stellar}GDEK5KGFA3WCG3F2MLSXFGLR4T4M6W6BMGWY6FBDSDQM6HXFMRSTEWBW) / \
[Wallet]({link_stellar}GB72L53HPZ2MNZQY4XEXULRD6AHYLK4CO55YTOBZUEORW2ZTSOEQ4MTL) / \
[Бот сжигания]({link_stellar}GD44EAUQXNUVBJACZMW6GPT2GZ7I26EDQCU5HGKUTVEQTXIDEVGUFIRE) 
Видео [Как подписывать](https://t.me/MTL_production/26) / [Как проверять](https://t.me/MTL_production/27) / [Как склеить\редактировать транзакции](https://t.me/MTL_production/28)
"""


@update_command_info("/start", "начать все с чистого листа")
@router.message(CommandStart(deep_link=False, magic=F.args.is_(None)), F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext, session: Session, bot: Bot):
    await state.clear()
    ChatsRepository(session).save_bot_user(message.from_user.id, message.from_user.username)
    await message.reply(startmsg)


ALL_EMOJI = """👍 👎 ❤ 🔥 🥰 👏 😁 🤔 🤯 😱 🤬 😢 🎉 🤩 🤮 💩 🙏 👌 🕊 🤡 🥱 🥴 😍 🐳 ❤‍🔥 🌚 🌭 💯 🤣 ⚡ 🍌 🏆 💔 
               🤨 😐 🍓 🍾 💋 🖕 😈 😴 😭 🤓 👻 👨‍💻 👀 🎃 🙈 😇 😨 🤝 ✍ 🤗 🫡 🎅 🎄 ☃ 💅 🤪 🗿 🆒 💘 🙉 🦄 😘 💊 
               🙊 😎 👾 🤷‍♂ 🤷 🤷‍♀ 😡""".split()


@router.message(Command("emoji"), F.chat.type == "private")
async def cmd_emoji(message: Message, state: FSMContext, session: Session, bot: Bot):
    args = message.text.split()[1:]

    if not args:
        await message.answer("Используйте: /emoji [all | URL | URL emoji]")
        return

    if args[0] == "all":
        await message.answer(f"Доступные эмодзи:\n{' '.join(ALL_EMOJI)}")
    elif args[0].startswith("https://t.me/"):
        chat_id, message_id = map(int, args[0].split('/')[-2:])
        emoji = args[1] if len(args) > 1 and args[1] in ALL_EMOJI else "👀"
        await bot.set_message_reaction(
            chat_id=f"-100{chat_id}",
            message_id=message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)]
        )
        await message.answer(f"Реакция {emoji} добавлена к сообщению.")
    else:
        await message.answer("Неверный формат команды.")


@router.message(Command(commands=["save"]))
async def cmd_save(message: Message):
    logger.info(f'{message.model_dump_json(indent=2)}')
    if message.from_user.id == MTLChats.ITolstov:
        await message.answer("Готово")
    else:
        await message.answer('Saved')


@update_command_info("/links", "показать полезные ссылки")
@router.message(Command(commands=["links"]))
async def cmd_links(message: Message):
    await message.answer(links_msg, parse_mode=ParseMode.MARKDOWN)


@update_command_info("/show_id", "Показать ID чата")
@router.message(Command(commands=["show_id"]))
async def cmd_show_id(message: Message):
    await message.answer(f"chat_id = {message.chat.id} message_thread_id = {message.message_thread_id} " +
                         f"is_topic_message  = {message.is_topic_message}")


@router.message(Command(commands=["me"]))
async def cmd_me(message: Message, bot: Bot):
    msg = ' '.join(message.text.split(' ')[1:])
    msg = f'<i><b>{message.from_user.username}</b> {msg}</i>'
    await bot.send_message(chat_id=message.chat.id, text=msg, parse_mode=ParseMode.HTML,
                           reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None,
                           message_thread_id=None if message.reply_to_message else message.message_thread_id)
    try:
        await message.delete()
    except:
        pass

@update_command_info("/link", "показать ссылки на Stellar адреса из сообщения")
@router.message(Command(commands=["link"]))
async def cmd_link(message: Message, bot: Bot):
    # Check if the command is a reply to a message
    if not message.reply_to_message:
        await message.reply("Эта команда должна быть использована в ответ на сообщение.")
        return

    replied_message_text = message.reply_to_message.html_text
    if not replied_message_text:
        await message.reply("В сообщении, на которое вы ответили, нет текста для поиска адресов.")
        return

    # Find Stellar addresses (56 characters, starting with G)
    stellar_addresses = re.findall(r'\b(G[A-Z0-9]{55})\b', replied_message_text)

    if not stellar_addresses:
        await message.reply("Stellar адреса не найдены в сообщении.")
        return

    # Remove duplicates and sort to ensure consistent order
    unique_stellar_addresses = sorted(list(set(stellar_addresses)))

    response_parts = []
    for address in unique_stellar_addresses:
        short_address = f"{address[:4]}..{address[-4:]}"
        stellar_expert_link = f"https://viewer.eurmtl.me/account/{address}"
        bsn_expert_link = f"https://bsn.expert/accounts/{address}"
        response_parts.append(
            f'{short_address} <a href="{stellar_expert_link}">viewer.eurmtl.me</a>  '
            f'<a href="{bsn_expert_link}">bsn.expert</a>'
        )
    if response_parts:
        full_response = "\n\n".join(response_parts)
        await message.reply(
            full_response,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    else:
        # This case should ideally not be reached if stellar_addresses is not empty,
        # but as a fallback.
        await message.reply("Не удалось сформировать ответ для найденных адресов.")

def register_handlers(dp, bot):
    dp.include_router(router)
    logger.info('router start_router was loaded')

register_handlers.priority = 10