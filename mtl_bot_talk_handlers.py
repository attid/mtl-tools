from aiogram import types
from aiogram.types import ChatType
import dialog
import mtl_bot_poll_handlers
import mystellar
import re, random
import update_report
import update_report2
import update_report4
from mtl_bot_main import dp


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


#@dp.message_handler(state='*')  # chat_type=[ChatType.PRIVATE, ChatType.SUPERGROUP]
async def cmd_last_check(message: types.Message):
    if message.text.find('mtl.ergvein.net/view') > -1:
        mystellar.cmd_save_url(message.chat.id, message.message_id, message.text)
        # print(message)
        # print(message.chat)
        await message.pin()

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
            msg_id = mystellar.cmd_load_bot_value(mystellar.BotValueTypes.PinnedId, message.chat.id)
            msg = mystellar.cmd_alarm_url(message.chat.id) + '\nСмотрите закреп / Look at the pinned message'
            await dp.bot.send_message(message.chat.id, msg, reply_to_message_id=msg_id)
        #            await message.reply(mystellar.cmd_alarm_url(message.chat.id) + '\nСмотрите закреп')

        elif has_words(message.text, ['ОБНОВИ', 'update']):
            if has_words(message.text, ['ГАРАНТОВ']):
                await message.reply('Зай, я запустила обновление')
                update_report2.update_guarant_report()
            if has_words(message.text, ['ОТЧЕТ', 'отчёт', 'report']):
                await message.reply('Зай, я запустила обновление')
                update_report.update_main_report()
            if has_words(message.text, ['donate', 'donates', 'donated']):
                await message.reply('Зай, я запустила обновление')
                update_report4.update_donate_report()

        elif has_words(message.text, ['ВЫПЬЕМ', 'ТОСТ']):
            await message.answer(mystellar.cmd_get_info(6))

        elif has_words(message.text, ['АНЕКДОТ']):
            await message.answer(mystellar.cmd_get_info(1))

        elif has_words(message.text, ['ХОРОШИЙ', 'МОЛОДЕЦ', 'УМНИЦА']):
            await message.reply('Спасибо ^_^')

        elif has_words(message.text, ['ГОТОВО', 'Signed']):
            await message.reply('Молодец ! Держи пирожок <ooo>')

        elif has_words(message.text, ['похвали', 'Поддержи']):
            await message.reply(f'{message.text.split()[2]} Молодец !')

        elif has_words(message.text, ['кто молчит', 'найди молчунов', 'найди безбилетника']):
            await mtl_bot_poll_handlers.cmd_poll_check(message)

        elif has_words(message.text, ['покажи']) and has_words(message.text, ['сиськи']):
            await message.reply_photo(random.choice(booms))

        elif has_words(message.text, ['хочется', 'нет', 'дай']) and has_words(message.text,
                                                                              ['стабильности', 'стабильность']):
            await message.reply_audio("CQACAgIAAxkBAAIITGIWcuo8u7-EFN_bFSw_0J0wyx6jAAJtFgACR8y5S2F0QnIe8RZMIwQ")

        else:
            await message.reply(dialog.talk(message.chat.id, message.text))

    elif message.chat.type == ChatType.PRIVATE:
        await message.reply(dialog.talk(message.chat.id, message.text))

    else:
        if message.reply_to_message and (message.reply_to_message.from_user.id == 2134695152):
            # answer on bot message
            await message.reply(dialog.talk(message.chat.id, message.text))
