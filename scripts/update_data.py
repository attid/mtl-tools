from utils.gspread_tools import get_assets_dict, get_accounts_dict
from utils.stellar_utils import *


@logger.catch
async def update_bim_in_id():
    agc = await agcm.authorize()
    now = datetime.now()
    wks_bim = gc.open("MTL_BIM_register").worksheet("List")
    wks_id = gc.open("MTL_ID_register").worksheet("List")

    data_bim = wks_bim.get_all_values()
    data_id = wks_id.get_all_values()

    list_bim_id = []

    for record in data_id[2:]:
        bim_id = None
        if len(record[5]) == 56:
            for bim in data_bim:
                if bim[4] == record[5]:
                    bim_id = bim[1]
                    break
        list_bim_id.append([bim_id])

    wks_id.update('AB3', list_bim_id)

    logger.info(f'all done {now}')


@logger.catch
async def update_id_in_bim():
    agc = await agcm.authorize()
    now = datetime.now()
    wks_bim = gc.open("MTL_BIM_register").worksheet("List")
    wks_id = gc.open("MTL_ID_register").worksheet("List")

    data_bim = wks_bim.get_all_values()
    data_id = wks_id.get_all_values()

    list_id = []

    for record_bim in data_bim[2:]:
        id_id = None
        if len(record_bim[4]) == 56:
            for record_id in data_id:
                if record_id[5] == record_bim[4]:
                    id_id = record_id[0]
                    break
        list_id.append([id_id])

    wks_bim.update('A3', list_id)

    logger.info(f'all done {now}')


async def update_tg_id():
    agc = await agcm.authorize()
    now = datetime.now()
    wks_id = gc.open("MTL_ID_register").worksheet("username")

    data_id = wks_id.get_all_values()

    update_list = []

    for record_id in data_id[1:]:
        # tg_name = None
        if len(record_id[0]) > 1 and record_id[0][0] == '@':
            tg_name = record_id[0][1:]
        else:
            tg_name = record_id[0]
        update_list.append([tg_name])

    wks_id.update('A2', update_list)

    logger.info(f'all done {now}')


async def update_tg_id_bim():
    agc = await agcm.authorize()
    now = datetime.now()
    wks_id = gc.open("MTL_ID_register").worksheet("username")

    data_id = wks_id.get_all_values()

    update_list = []

    for record_id in data_id[1:]:
        # tg_name = None
        if len(record_id[0]) > 1 and record_id[0][0] == '@':
            tg_name = record_id[0][1:]
        else:
            tg_name = record_id[0]
        update_list.append([tg_name])

    wks_id.update('A2', update_list)

    logger.info(f'all done {now}')


@logger.catch
async def update_id_in_bim():
    agc = await agcm.authorize()
    now = datetime.now()
    wks_bim = gc.open("MTL_BIM_register").worksheet("List")
    wks_id = gc.open("MTL_ID_register").worksheet("username")

    data_bim = wks_bim.get_all_values()
    data_id = wks_id.get_all_values()

    # list_id = []

    for idx, record_bim in enumerate(data_bim[2:]):
        if len(record_bim[2]) > 0 and len(record_bim[3]) > 0:
            pass
        else:
            if record_bim[2]:
                for record_id in data_id:
                    if record_id[0] == record_bim[2]:
                        wks_bim.update(f'D{idx + 3}', [[record_id[1]]])
                        # id_id = record_id[0]
                        print(record_id, record_bim, idx)

    logger.info(f'all done {now}')


async def update_memo():
    agc = await agcm.authorize()
    now = datetime.now()
    wks = gc.open("test export 4").worksheet("2023")

    data = wks.get_all_values()

    for idx, record in enumerate(data[1:]):
        if len(record[8]) > 0 and record[8] == MTLAddresses.public_issuer and len(record[9]) == 0:
            memo = get_memo_by_op(record[0].split('-')[0])
            print(idx, memo, record)
            wks.update(f'J{idx + 2}', [[memo]])

    logger.info(f'all done {now}')


async def update_lab():
    headers = {
        "Authorization": f"Bearer {config.eurmtl_key}",
        "Content-Type": "application/json"
    }
    print(await get_accounts_dict())
    async with aiohttp.ClientSession() as session:
        async with session.post("https://eurmtl.me/lab/mtl_accounts", headers=headers,
                                data=json.dumps(await get_accounts_dict())) as response:
            #print(response.status)
            logger.info(await response.text())

        async with session.post("https://eurmtl.me/lab/mtl_assets", headers=headers,
                                data=json.dumps(await get_assets_dict())) as response:
            logger.info(await response.text())


if __name__ == "__main__":
    logger.add("update_report.log", rotation="1 MB")
    logger.info(datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
    asyncio.run(update_lab())
