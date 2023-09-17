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
from keyboards.keyboards import yes_no_kb
from lexicon.lexicon import LEXICON_RU

from services.db_func import get_or_create_user
from services.order_func import create_order, get_case_text, get_case_from_order

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


@router.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext, bot: Bot):
    logger.debug(f'/start {message.from_user.id}')
    await state.clear()
    referal = message.text[7:]
    new_user = get_or_create_user(message.from_user, referal)
    await message.answer(LEXICON_RU['start_text'])


def response_order_url(message: Message) -> str:
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
    msg: Message = await bot.send_message(chat_id=GROUP_ID, text=text)
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



@router.callback_query()
async def stat(callback: CallbackQuery, state: FSMContext, bot: Bot):
    print('echo')
    print(callback.data)


@router.message()
async def order(message: Message, state: FSMContext, bot: Bot):
    print('echo message')
