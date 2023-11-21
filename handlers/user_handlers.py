import datetime

from aiogram import Router, Bot, F
from aiogram.filters import Command, ChatMemberUpdatedFilter, MEMBER, LEFT, ADMINISTRATOR, KICKED, StateFilter, \
    BaseFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, ChatInviteLink, \
    InlineKeyboardButton, ChatMemberUpdated, FSInputFile

from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import Text

from config_data.conf import tz, get_my_loggers, conf
from database.db import Order
from keyboards.keyboards import yes_no_kb, start_kb, custom_kb
from lexicon.lexicon import LEXICON_RU

from services.db_func import get_or_create_user
from services.order_func import create_order, get_case_text, get_case_from_order, get_my_orders, delete_order, \
    get_case_from_order_id

logger, err_log = get_my_loggers()

router: Router = Router()


class IsPrivate(BaseFilter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message, *args) -> bool:
        if isinstance(message, Message):
            return message.chat.type == 'private'
        elif isinstance(message, CallbackQuery):
            return message.message.chat.type == 'private'


class FSMOrder(StatesGroup):
    order = State()


@router.callback_query(F.data == 'cancel')
async def stat(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    await state.clear()
    await callback.message.answer(LEXICON_RU['start_text'], reply_markup=start_kb)


@router.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext, bot: Bot):
    logger.debug(f'/start {message.from_user.id}')
    await state.clear()
    referal = message.text[7:]
    new_user = get_or_create_user(message.from_user, referal)
    await message.answer(LEXICON_RU['start_text'], reply_markup=start_kb)


def response_order_url(message: Message) -> str:
    print(message)
    domen = 'dw4.co'
    order_url = ''
    if message.entities:
        for entity in message.entities:
            if entity.type == 'url':
                url = message.text[entity.offset:entity.offset+entity.length]
                if domen in url:
                    order_url = url
                    break
    return order_url
    

@router.message(IsPrivate())
async def order(message: Message, state: FSMContext, bot: Bot):
    print(message)
    order_url = response_order_url(message)
    if order_url:
        await state.set_state(FSMOrder.order)
        await state.update_data(text=message.text, link=order_url, order_message=message)
        text = f'<b>Подтвердите заказ!</b>\n\n {message.text} '
        await message.answer(text=text, reply_markup=yes_no_kb)


async def refresh_order_message(bot: Bot, case):
    GROUP_ID = conf.tg_bot.GROUP_ID
    text = get_case_text()
    # msg: Message = await bot.send_message(chat_id=GROUP_ID, text=text)
    msg: Message = await bot.send_video(GROUP_ID, video='BAACAgIAAxkBAAIC2GVcUAYX7lNQmmr2yXCs2E2qRrrWAAL-MwACVwLpSptg2XddHo5OMwQ')
    msg_url = msg.get_url(force_private=True)
    old_msg_id = case.msg_id
    if old_msg_id:
        await bot.delete_message(chat_id=GROUP_ID, message_id=old_msg_id)
    case.set('msg_id', msg.message_id)


@router.callback_query(F.data == 'confirm')
async def stat(callback: CallbackQuery, state: FSMContext, bot: Bot):
    print('confirm')
    data = await state.get_data()
    await callback.message.edit_reply_markup()
    user = get_or_create_user(callback.from_user)
    new_order = create_order(user=user, text=data.get('text'), link=data.get('link'))
    logger.info(f'Заказ создан: {new_order}')
    await callback.message.answer('Заказ создан')
    await state.clear()
    await callback.message.edit_text(text=callback.message.text + '\nЗаказ принят')

    # Действия в группе
    GROUP_ID = conf.tg_bot.GROUP_ID
    text = get_case_text()
    # msg: Message = await bot.send_message(chat_id=GROUP_ID, text=text)
    msg: Message = await bot.send_video(GROUP_ID,
                                        video='BAACAgIAAxkBAAIC2GVcUAYX7lNQmmr2yXCs2E2qRrrWAAL-MwACVwLpSptg2XddHo5OMwQ', caption=text)
    msg_url = msg.get_url(force_private=True)
    await callback.message.answer(text=f'Ссылка на заказ: {msg_url}')
    case = get_case_from_order(new_order)
    old_msg_id = case.msg_id
    if old_msg_id:
        await bot.delete_message(chat_id=GROUP_ID, message_id=old_msg_id)
    case.set('msg_id', msg.message_id)

    group = await bot.get_chat(chat_id=GROUP_ID)
    print(group)
    print(type(group))


@router.callback_query(F.data == 'delete_order')
async def delete(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    orders: list[Order] = get_my_orders(callback.from_user.id)
    text = 'Заказы доступные для удаления:\n\n'
    kb = {}
    for order in orders:
        if order.case.status == 1:
            text += f'№ {order.id} от {order.created.strftime("%d.%m.%Y")}: {order.link}\n\n'
            kb[f'{str(order.id)}'] = f'delete_order_{order.id}'
    if text != 'Заказы доступные для удаления:\n\n':
        text += 'Выберите заказ для для удаления:'
        kb['Отменить'] = 'cancel'
        await callback.message.answer(text=text, reply_markup=custom_kb(1, kb))
    await callback.message.answer('Заказов нет')


@router.callback_query(F.data.startswith('delete_order_'))
async def delete(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    order_id = callback.data.split('delete_order_')[1]
    order_id = int(order_id)

    logger.debug(f'Удаялем заказ {order_id}')
    is_delete = delete_order(order_id)
    if is_delete:
        await callback.message.answer('Ваш заказ удален')
        # Обновить сообщение
        case = get_case_from_order_id(order_id)
        await refresh_order_message(bot, case)

    else:
        await callback.message.answer('Произошла ошибка при удалении. Возможно заказ уже сформирован')





@router.callback_query()
async def stat(callback: CallbackQuery, state: FSMContext, bot: Bot):
    print('echo')
    print(callback.data)


@router.message()
async def order(message: Message, state: FSMContext, bot: Bot):
    print('echo message')
