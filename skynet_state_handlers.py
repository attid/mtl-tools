from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import mystellar
from skynet_main import dp


# from aiogram.utils.markdown import bold, code, italic, text, link

# https://docs.aiogram.dev/en/latest/quick_start.html
# https://surik00.gitbooks.io/aiogram-lessons/content/chapter3.html


class MyStates(StatesGroup):
    # mode = HelperMode.snake_case
    dron2_1 = State()  # Will be represented in storage as 'MyStates:dron2_1'
    dron2_2 = State()
    dron2_3 = State()
    mtl_camp_1 = State()
    mtl_camp_2 = State()
    mtl_camp_3 = State()
    bl_add1 = State()
    bl_add2 = State()
    bl_add3 = State()
    bl_delete = State()
    edit_xdr_1 = State()
    edit_xdr_2 = State()
    edit_xdr_3 = State()
    edit_xdr_4 = State()
    edit_xdr_5 = State()
    edit_xdr_6 = State()


#################################################################
################           drone2                ################
#################################################################

@dp.message_handler(commands="dron2")
async def cmd_dron20(message: types.Message):
    await MyStates.dron2_1.set()
    await message.reply('Пришлите ваш публичный адрес')


@dp.message_handler(state=MyStates.dron2_1, commands="sign")
async def cmd_dron21(message: types.Message):
    await MyStates.dron2_2.set()
    await message.reply('Пришлите ваш секретный ключ')


@dp.message_handler(state=MyStates.dron2_1)
async def smd_dron_tr(message: types.Message, state: FSMContext):
    try:
        xdr = mystellar.stellar_add_drone2(message.text)
    except ValueError:
        await message.reply('This is not a valid account. Try another.')
        return
    # except Exception:
    #    print('Это что ещё такое?')

    async with state.proxy() as data:
        data['xdr'] = xdr
    await message.reply('Ваша транзакция :')
    await message.reply(xdr)
    await message.reply('Вы можете ее подписать тут /sign или отправить сами и выйти /start')


@dp.message_handler(state=MyStates.dron2_2)
async def smd_dron_sign(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        xdr = data['xdr']
    signkey = message.text
    await message.delete()
    await message.answer('Ключ получил и удалил')
    try:
        xdr = mystellar.stellar_sign(xdr, signkey)
    except:
        await message.answer('This is not a valid key. Try another.')
        return
    await message.answer('Ваша транзакция с подписью :')
    await message.answer(xdr)
    await message.answer('Попытка отправить')

    resp = await mystellar.stellar_submite(xdr)

    await message.answer(resp)
    await message.answer('Вы можете выйти /start')


#################################################################
################           editxdr               ################
#################################################################

async def cmd_xdr_msg(message, trList):
    await message.reply(f'В работе транзакция {trList[1]} в ней {trList[2]} операции')
    await message.reply(
        'Вы можете посмотреть /show получить /xdr \n удалить операцию по номеру "/del 0" \n' +
        'сменить номер sequence "/sequence 2525" \nсменить комиссию "/fee 100"  \n' +
        'удалить подпись по номеру "/delsign 0" \n' +
        'сменить memo "/memo bla bla bla" \nили приклеить транзакцию /add или выйти /start')


@dp.message_handler(commands="editxdr")
async def cmd_editxdr(message: types.Message):
    await MyStates.edit_xdr_1.set()
    await message.reply('Пришлите транзакцию для редактирования')


@dp.message_handler(state=MyStates.edit_xdr_1)
async def smd_editxdr2(message: types.Message, state: FSMContext):
    try:
        trList = mystellar.stellar_check_xdr(message.text)
    except ValueError:
        await message.reply('This is not a valid xdr. Try another.')
        return
    async with state.proxy() as data:
        data['xdr'] = trList[0]
    await MyStates.edit_xdr_2.set()
    await cmd_xdr_msg(message, trList)


@dp.message_handler(state=MyStates.edit_xdr_2, commands="show")
async def smd_editxdr3(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        xdr = data['xdr']
    trList = mystellar.stellar_check_xdr(xdr)
    msg = mystellar.decode_xdr(xdr)
    msg = f'\n'.join(msg)
    if len(msg) > 4096:
        await message.answer("Слишком много операций показаны первые ")
    await message.answer(msg[0:4000])
    await cmd_xdr_msg(message, trList)
    # if len(info) > 4096:
    # for x in range(0, len(info), 4096):
    #    bot.send_message(message.chat.id, info[x:x+4096])
    # else:
    #    bot.send_message(message.chat.id, info)


@dp.message_handler(state=MyStates.edit_xdr_2, commands="xdr")
async def smd_editxdr4(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        xdr = data['xdr']
    await message.reply(xdr)
    trList = mystellar.stellar_check_xdr(xdr)
    await cmd_xdr_msg(message, trList)


@dp.message_handler(state=MyStates.edit_xdr_2, commands="sequence")
async def smd_editxdr5(message: types.Message, state: FSMContext):
    if message.get_args().isnumeric():
        num = int(message.get_args())
        async with state.proxy() as data:
            xdr = data['xdr']
        trList = mystellar.stellar_set_sequence(xdr, num)
        async with state.proxy() as data:
            data['xdr'] = trList[0]
        await cmd_xdr_msg(message, trList)
    else:
        await message.reply(f'Параметр не распознан. Надо передавать число')


@dp.message_handler(state=MyStates.edit_xdr_2, commands="fee")
async def smd_editxdr51(message: types.Message, state: FSMContext):
    if message.get_args().isnumeric():
        num = int(message.get_args())
        async with state.proxy() as data:
            xdr = data['xdr']
        trList = mystellar.stellar_set_fee(xdr, num)
        async with state.proxy() as data:
            data['xdr'] = trList[0]
        await cmd_xdr_msg(message, trList)
    else:
        await message.reply(f'Параметр не распознан. Надо передавать число')


@dp.message_handler(state=MyStates.edit_xdr_2, commands="memo")
async def smd_editxdr52(message: types.Message, state: FSMContext):
    if len(message.get_args()) > 1:
        async with state.proxy() as data:
            xdr = data['xdr']
        trList = mystellar.stellar_set_memo(xdr, message.get_args())
        async with state.proxy() as data:
            data['xdr'] = trList[0]
        await cmd_xdr_msg(message, trList)
    else:
        await message.reply(f'Параметр не распознан.')


@dp.message_handler(state=MyStates.edit_xdr_2, commands="del")
async def smd_editxdr6(message: types.Message, state: FSMContext):
    if message.get_args().isnumeric():
        num = int(message.get_args())
        async with state.proxy() as data:
            xdr = data['xdr']
        trList = mystellar.stellar_del_operation(xdr, num)
        async with state.proxy() as data:
            data['xdr'] = trList[0]
        await message.reply(f'Удалена {num}-я операция : {trList[3]}')
        await cmd_xdr_msg(message, trList)
    else:
        await message.reply(f'Параметр не распознан. Надо передавать число')


@dp.message_handler(state=MyStates.edit_xdr_2, commands="delsign")
async def smd_editxdr63(message: types.Message, state: FSMContext):
    if message.get_args().isnumeric():
        num = int(message.get_args())
        async with state.proxy() as data:
            xdr = data['xdr']
        trList = mystellar.stellar_del_sign(xdr, num)
        async with state.proxy() as data:
            data['xdr'] = trList[0]
        await message.reply(f'Удалена {num}-я операция : {trList[3]}')
        await cmd_xdr_msg(message, trList)
    else:
        await message.reply(f'Параметр не распознан. Надо передавать число')


@dp.message_handler(state=MyStates.edit_xdr_2, commands="add")
async def smd_editxdr7(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        xdr = data['xdr']
    await message.reply(
        'Пришлите новую транзакцию, номер и адресат берется из первой транзакции из второй только операции')
    await MyStates.edit_xdr_3.set()


@dp.message_handler(state=MyStates.edit_xdr_3)
async def smd_editxdr8(message: types.Message, state: FSMContext):
    try:
        trList2 = mystellar.stellar_check_xdr(message.text)
    except ValueError:
        await message.reply('This is not a valid xdr. Try another.')
        return
    async with state.proxy() as data:
        data['xdr2'] = trList2[0]
        xdr = data['xdr']
        trList = mystellar.stellar_check_xdr(xdr)
    await message.reply(f'В работе транзакция {trList[1]} в ней {trList[2]} операции')
    await message.reply(f'Добавляется транзакция {trList2[1]} в ней {trList2[2]} операции')
    trList = mystellar.stellar_add_xdr(xdr, trList2[0])
    async with state.proxy() as data:
        data['xdr'] = trList[0]
    await MyStates.edit_xdr_2.set()
    await cmd_xdr_msg(message, trList)


#################################################################
################           mtlcamp               ################
#################################################################

@dp.message_handler(commands="mtlcamp")
async def cmd_mtlcamp0(message: types.Message):
    await MyStates.mtl_camp_1.set()
    await message.reply('Пришлите ваш публичный адрес')


@dp.message_handler(state=MyStates.mtl_camp_1, commands="sign")
async def cmd_mtlcamp1(message: types.Message):
    await MyStates.mtl_camp_2.set()
    await message.reply('Пришлите ваш секретный ключ')


@dp.message_handler(state=MyStates.mtl_camp_1)
async def smd_mtl_camp_tr(message: types.Message, state: FSMContext):
    try:
        xdr = mystellar.stellar_add_mtlcamp(message.text)
    except ValueError:
        await message.reply('This is not a valid account. Try another.')
        return
    # except Exception:
    #    print('Это что ещё такое?')

    async with state.proxy() as data:
        data['xdr'] = xdr
    await message.reply('Ваша транзакция :')
    await message.reply(xdr)
    await message.reply('Вы можете ее подписать тут /sign или отправить сами и выйти /start')


@dp.message_handler(state=MyStates.mtl_camp_2)
async def smd_mtl_camp_sign(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        xdr = data['xdr']
    signkey = message.text
    await message.delete()
    await message.answer('Ключ получил и удалил')
    try:
        xdr = mystellar.stellar_sign(xdr, signkey)
    except:
        await message.answer('This is not a valid key. Try another.')
        return
    await message.answer('Ваша транзакция с подписью :')
    await message.answer(xdr)
    await message.answer('Попытка отправить')

    resp = await mystellar.stellar_submite(xdr)

    await message.answer(resp)
    await message.answer('Вы можете выйти /start')

#################################################################
################        ________                ################
#################################################################
