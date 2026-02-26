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
from services.order_func import create_order, get_order_text, get_my_orders, delete_order, get_case_from_order_id

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
async def process_cancel(callback: CallbackQuery, state: FSMContext, bot: Bot):
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
    

@router.message(F.video, F.from_user.id.in_(frozenset(int(x) for x in conf.tg_bot.admin_ids if x)))
async def process_admin_video(message: Message, bot: Bot):
    """При отправке видео админом — отвечаем file_id для использования в ORDER_VIDEO_FILE_ID."""
    file_id = message.video.file_id
    logger.info(f'Админ {message.from_user.id} отправил видео, file_id: {file_id}')
    await message.reply(f'<code>{file_id}</code>\n\nСкопируй в .env как ORDER_VIDEO_FILE_ID')


@router.message(IsPrivate())
async def order(message: Message, state: FSMContext, bot: Bot):
    # print(message)
    order_url = response_order_url(message)
    if order_url:
        await state.set_state(FSMOrder.order)
        await state.update_data(text=message.text, link=order_url, order_message=message)
        text = f'<b>Подтвердите заказ!</b>\n\n {message.text} '
        await message.answer(text=text, reply_markup=yes_no_kb)


@router.callback_query(F.data == 'confirm')
async def process_confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение заказа: создаём заказ, отправляем в группу и пользователю."""
    data = await state.get_data()
    await callback.message.edit_reply_markup()
    user = get_or_create_user(callback.from_user)
    new_order = create_order(user=user, text=data.get('text'), link=data.get('link'))
    logger.info(f'Заказ создан: {new_order}')

    order_text = get_order_text(user, new_order)
    video_id = conf.tg_bot.ORDER_VIDEO_FILE_ID
    GROUP_ID = conf.tg_bot.GROUP_ID

    # Отправляем в группу: видео + текст
    msg: Message = await bot.send_video(GROUP_ID, video=video_id, caption=order_text)
    msg_url = msg.get_url(force_private=True)

    # Сохраняем msg_id в кейс (для удаления сообщения при отмене заказа)
    case = get_case_from_order_id(new_order.id)
    if case:
        case.set('msg_id', msg.message_id)

    # Отправляем пользователю подтверждение
    await callback.message.edit_text(text=callback.message.text + '\n\n✅ Заказ принят')
    await callback.message.answer(text=order_text)
    await callback.message.answer(text=f'Ссылка на заказ в группе: {msg_url}')
    await state.clear()


@router.callback_query(F.data == 'delete_order')
async def process_delete_order_list(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Показать список заказов для удаления."""
    await callback.message.delete()
    orders: list[Order] = get_my_orders(callback.from_user.id)
    text = 'Заказы доступные для удаления:\n\n'
    kb = {}
    for order in orders:
        text += f'№ {order.id} от {order.created.strftime("%d.%m.%Y")}: {order.link}\n\n'
        kb[f'№ {order.id}'] = f'delete_order_{order.id}'
    if kb:
        text += 'Выберите заказ для удаления:'
        kb['Отменить'] = 'cancel'
        await callback.message.answer(text=text, reply_markup=custom_kb(1, kb))
    else:
        await callback.message.answer('Заказов нет')


@router.callback_query(F.data.startswith('delete_order_'))
async def process_delete_order_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Удаление выбранного заказа и сообщения в группе."""
    await callback.message.delete()
    order_id = int(callback.data.split('delete_order_')[1])
    logger.debug(f'Удаляем заказ {order_id}')

    case = get_case_from_order_id(order_id)
    case_msg_id = case.msg_id if case else None

    is_deleted = delete_order(order_id)
    if is_deleted:
        GROUP_ID = conf.tg_bot.GROUP_ID
        if case_msg_id:
            try:
                await bot.delete_message(chat_id=GROUP_ID, message_id=int(case_msg_id))
            except Exception as err:
                logger.debug(f'Сообщение {case_msg_id} в группе не удалено: {err}')
        await callback.message.answer('Ваш заказ удалён')
    else:
        await callback.message.answer('Произошла ошибка при удалении')


# @router.callback_query()
# async def stat(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     print('echo')
#     print(callback.data)
#
#
# @router.message()
# async def order(message: Message, state: FSMContext, bot: Bot):
#     logger.debug(message)

