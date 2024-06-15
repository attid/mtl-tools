from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReactionTypeEmoji
from loguru import logger
from sqlalchemy.orm import Session

from db.requests import db_save_bot_user
from middlewares.sentry_error_handler import sentry_error_handler
from utils.global_data import MTLChats, update_command_info
from utils.stellar_utils import MTLAddresses

router = Router()
router.error()(sentry_error_handler)

startmsg = """
Привет, я бот из <a href="https://montelibero.org">Монтелиберо</a>.
Помогаю справляться с задачами, либо просто можем пообщаться.
Чтобы увидеть все, что я умею, наберите в поле ввода @mymtlbot и любое слово для поиска команды
"""

link_stellar = "https://stellar.expert/explorer/public/account/"
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
@router.message(F.text.lower() == "/start", F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext, session: Session, bot: Bot):
    await state.clear()
    db_save_bot_user(session, message.from_user.id, message.from_user.username)
    await message.reply(startmsg)
    #await bot.set_message_reaction(message.chat.id, message.message_id, ["🔥"])
    #if message.reply_to_message:
    #    await message.reply_to_message.react([ReactionTypeEmoji(emoji="👎")])
    #await bot.set_message_reaction(
    #    chat_id=message.chat.id,
    #    message_id=message.message_id,
    #    reaction=[ReactionTypeEmoji(emoji="👍"), ReactionTypeEmoji(emoji="👎")],
    #)



@router.message(Command(commands=["save"]))
async def cmd_save(message: Message):
    logger.info(f'{message.json()}')
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
