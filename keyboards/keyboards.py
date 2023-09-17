from aiogram.types import KeyboardButton, ReplyKeyboardMarkup,\
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder



kb1 = {
    # 'Мои заказы': 'my_orders',
    'Удалить заказ': 'delete_order',
}


def custom_kb(width: int, buttons_dict: dict) -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    buttons = []
    for key, val in buttons_dict.items():
        callback_button = InlineKeyboardButton(
            text=key,
            callback_data=val)
        buttons.append(callback_button)
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


start_kb = custom_kb(2, kb1)


yes_no_kb_btn = {
    'Отменить': 'cancel',
    'Подтвердить': 'confirm',
}

yes_no_kb = custom_kb(2, yes_no_kb_btn)
