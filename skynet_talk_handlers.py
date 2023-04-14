from aiogram import types
from aiogram.types import ChatType, ParseMode
import dialog
import skynet_poll_handlers
import mystellar
import re, random
import update_report
import update_report2
import update_report4
from skynet_main import dp, is_skynet_admin, MTLChats, reply_only, send_by_list
from loguru import logger


# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html

# @dp.message_handler(chat_type=ChatType.PRIVATE) #chat_type=[ChatType.PRIVATE, ChatType.SUPERGROUP]
# async def echo(message: types.Message):
#    # old style:
#    # await bot.send_message(message.chat.id, message.text)
#    #await message.answer("You say "+message.text)
#    await message.answer(startmsg)
#    state = dp.current_state(user=message.from_user.id)
#    await state.reset_state()
#    #print(message.chat)
def has_words(master, words_array):
    for word in words_array:
        if master.upper().find(word.upper()) > -1:
            return True
    return False


booms = ["AgACAgIAAxkBAAIINGIWWwHuiOBgxuBQ9CBnfL7-VPXVAALuuzEbbLOxSFW75wtHIJnnAQADAgADbQADIwQ",
         "AgACAgIAAxkBAAIINWIWWx7J93iRTnwFTuMAAcYa8At2NwAC77sxG2yzsUhQ3cKwVLCxaAEAAwIAA20AAyME",
         "AgACAgIAAxkBAAIINmIWWzm8y-aDIF9fKLQqjdOMMfx4AALwuzEbbLOxSOot27VAmmSdAQADAgADeAADIwQ",
         "AgACAgIAAxkBAAIIN2IWW1Pq8xtfB-wHiMVVzNVCRk5iAALyuzEbbLOxSJ7cQZ9NcU-HAQADAgADbQADIwQ", ]

my_talk_message = []


@dp.message_handler(commands="skynet")
async def cmd_skynet(message: types.Message):
    await cmd_last_check(message)


# @dp.message_handler(state='*')  # chat_type=[ChatType.PRIVATE, ChatType.SUPERGROUP]
async def cmd_last_check(message: types.Message):
    if message.text.find('eurmtl.me/sign_tools') > -1:
        msg_id = mystellar.cmd_load_bot_value(mystellar.BotValueTypes.PinnedId, message.chat.id)
        try:
            await dp.bot.unpin_chat_message(message.chat.id, msg_id)
        except:
            pass
        mystellar.cmd_save_url(message.chat.id, message.message_id, message.text)
        await message.pin()
        if message.chat.id in (MTLChats.SignGroup.value, MTLChats.TestGroup.value, MTLChats.ShareholderGroup.value,
                               MTLChats.SafeGroup.value, MTLChats.LandLordGroup.value, MTLChats.SignGroupForChanel.value):
            msg = mystellar.check_url_xdr(
                mystellar.cmd_load_bot_value(mystellar.BotValueTypes.PinnedUrl, message.chat.id))
            msg = f'\n'.join(msg)
            if len(msg) > 4096:
                await message.answer("Слишком много операций показаны первые ")
            await message.reply(msg[:4000])

        if message.chat.id in (MTLChats.SignGroup.value,MTLChats.SignGroupForChanel.value,):
            msg = mystellar.cmd_alarm_pin_url(message.chat.id) + '\nСмотрите закреп / Look at the pinned message'
            await message.reply(msg)

    if message.chat.id in reply_only:
        if message.reply_to_message or message.forward_from_chat:
            pass
        else:
            await message.reply('Осуждаю ! Это сообщения не увидят в комментариях. '
                                'Рекомендую удалить его, и повторить его с использованием функции «ответ». \n'
                                'Ещё проще, если переписываться из комментариев к исходному посту в канале.')
            return

    if has_words(message.text, ['Кузя', 'Скайнет', 'prst', 'skynet']):  # message.text.upper().find('СКАЙНЕТ') > -1
        if has_words(message.text, ['УБИТЬ', 'убей', 'kill']):
            await message.answer('Нельзя убивать. NAP NAP NAP')

        elif has_words(message.text, ['ДЕКОДИРУЙ', 'decode']):
            msg = mystellar.check_url_xdr(
                mystellar.cmd_load_bot_value(mystellar.BotValueTypes.PinnedUrl, message.chat.id))
            msg = f'\n'.join(msg)
            if len(msg) > 4096:
                await message.answer("Слишком много операций показаны первые ")
            await message.reply(msg[:4000])

        elif has_words(message.text, ['СГЕНЕРИ', 'сделай', 'подготовь']):
            if has_words(message.text, ['ДИВИДЕНДЫ', 'дивы']):
                await message.reply(mystellar.cmd_gen_div_xdr(float(re.findall(r'\d+', message.text)[0])))

        elif has_words(message.text, ['НАПОМНИ', 'remind']):
            await remind(message)

        elif has_words(message.text, ['ОБНОВИ', 'update']):
            if not await is_skynet_admin(message):
                await message.reply('You are not my admin.')
                return False
            if has_words(message.text, ['ГАРАНТОВ']):
                msg = await message.reply('Зай, я запустила обновление')
                await update_report2.update_guarantors_report()
                await msg.reply('Обновление завершено')
            if has_words(message.text, ['ОТЧЕТ', 'отчёт', 'report']):
                msg = await message.reply('Зай, я запустила обновление')
                await update_report.update_main_report()
                await update_report.update_fire()
                await msg.reply('Обновление завершено')
            if has_words(message.text, ['donate', 'donates', 'donated']):
                msg = await message.reply('Зай, я запустила обновление')
                await update_report4.update_donate_report()
                await msg.reply('Обновление завершено')

        # elif has_words(message.text, ['ВЫПЬЕМ', 'ТОСТ']):
        #    await message.answer(mystellar.cmd_get_info(6))

        # elif has_words(message.text, ['АНЕКДОТ']):
        #    await message.answer(mystellar.cmd_get_info(1))

        elif has_words(message.text, ['гороскоп']):
            await message.answer('\n'.join(dialog.get_horoscope()), parse_mode=ParseMode.MARKDOWN)

        # elif has_words(message.text, ['ХОРОШИЙ', 'МОЛОДЕЦ', 'УМНИЦА']):
        #    await message.reply('Спасибо ^_^')

        # elif has_words(message.text, ['ГОТОВО', 'Signed']):
        #    await message.reply('Молодец ! Держи пирожок <ooo>')

        # elif has_words(message.text, ['похвали', 'Поддержи']):
        #    await message.reply(f'{message.text.split()[2]} Молодец !')

        elif has_words(message.text, ['кто молчит', 'найди молчунов', 'найди безбилетника']):
            await skynet_poll_handlers.cmd_poll_check(message)

        elif has_words(message.text, ['покажи']) and has_words(message.text, ['сиськи']):
            await message.reply_photo(random.choice(booms))

        elif has_words(message.text, ['сколько']) and has_words(message.text, ['кубышк']):
            result = await mystellar.get_safe_balance()
            await message.reply(result)

        elif has_words(message.text, ['хочется', 'нет', 'дай']) and has_words(message.text,
                                                                              ['стабильности', 'стабильность']):
            await message.reply_audio("CQACAgIAAxkBAAIITGIWcuo8u7-EFN_bFSw_0J0wyx6jAAJtFgACR8y5S2F0QnIe8RZMIwQ")

        else:
            msg = await dialog.talk(message.chat.id, message.text)
            msg = await message.reply(msg)
            my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')

    elif message.chat.type == ChatType.PRIVATE:
        msg = await dialog.talk(message.chat.id, message.text)
        msg = await message.reply(msg)

    else:
        if message.reply_to_message and (message.reply_to_message.from_user.id == 2134695152) \
                and (f'{message.reply_to_message.message_id}*{message.chat.id}' in my_talk_message):
            # answer on bot message
            msg = await dialog.talk(message.chat.id, message.text)
            msg = await message.reply(msg)
            my_talk_message.append(f'{msg.message_id}*{msg.chat.id}')


async def remind(message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        alarm_list = mystellar.cmd_alarm_url_(mystellar.extract_url(message.reply_to_message.text))
        msg =  alarm_list + '\nСмотрите топик / Look at the topic message'
        await message.reply(text=msg)
        if alarm_list.find('@') != -1:
            if await is_skynet_admin(message):
                all_users = alarm_list.split()
                url  = f'https://t.me/c/1649743884/{message.reply_to_message.forward_from_message_id}'
                await send_by_list(all_users, message, url=url)

    else:
        msg_id = mystellar.cmd_load_bot_value(mystellar.BotValueTypes.PinnedId, message.chat.id)
        msg = mystellar.cmd_alarm_pin_url(message.chat.id) + '\nСмотрите закреп / Look at the pinned message'
        await dp.bot.send_message(message.chat.id, msg, reply_to_message_id=msg_id,
                              message_thread_id=message.message_thread_id)
