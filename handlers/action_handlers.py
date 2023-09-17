import datetime

from aiogram import Router, Bot, F
from aiogram.filters import Command, ChatMemberUpdatedFilter, MEMBER, LEFT, ADMINISTRATOR, KICKED
from aiogram.types import CallbackQuery, Message, ChatInviteLink, \
    InlineKeyboardButton, ChatMemberUpdated


from config_data.conf import get_my_loggers, conf, BASE_DIR
from lexicon.lexicon import LEXICON_RU
from services.db_func import get_or_create_user

logger, err_log = get_my_loggers()

router: Router = Router()


# Действия юзеров
@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEFT))
@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def user_kick(event: ChatMemberUpdated, bot: Bot):
    logger.debug('USER KICKED or LEFT')
    try:
        chat = event.chat
        user = event.old_chat_member.user
        logger.info(f'Юзер {user.username} {user.id} KICKED/LEFT с канала {chat.id} {chat.title} ')
        user = get_or_create_user(user)

    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)
        raise err


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def user_join(event: ChatMemberUpdated, bot: Bot):
    # GROUP_ID = conf.tg_bot.GROUP_ID
    logger.debug('USER MEMBER')
    try:
        chat = event.chat
        member = event.new_chat_member.user
        logger.debug(f'member: {member}')
        logger.info(f'Юзер {member.username} {member.id} присоединился к каналу {chat.id} {chat.title} ')
        user = get_or_create_user(member)
        logger.debug(f'user: {user}')
        try:
            with open(BASE_DIR / 'msg.txt', 'r') as file:
                old_id = file.read().strip()
            if old_id:
                old_id = int(old_id)
                await bot.delete_message(chat_id=event.chat.id, message_id=old_id)
        except Exception as err:
            logger.error(err)
        with open(BASE_DIR / 'login.txt', 'r') as file:
            logins = file.read().split('\n')
        if event.from_user.username in logins:
            logger.debug('Не отправляем ссобщение')
            pass
        else:
            logger.debug(f'Отпраялем сообщение - добавлен {member}')
            msg = await bot.send_message(chat_id=event.chat.id,
                                         text=LEXICON_RU['hello_msg'].format(
                                             member.first_name or member.user.username))
            with open(BASE_DIR / 'msg.txt', 'w') as file:
                file.write(str(msg.message_id))


    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)
        raise err


# Действия бота
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def as_member(event: ChatMemberUpdated, bot: Bot):
    logger.debug('MY event MEMBER')
    try:
        chat = event.chat
        owner = event.from_user
        logger.info(f'Бот добавлен в канал {chat.id} {chat.title} как MEMBER  пользователем {owner.username} {owner.id}')
        # await bot.send_message(chat_id=owner.id, text=f'Бот добавлен в канал {chat.id} {chat.title} как MEMBER  пользователем {owner.username} {owner.id}')
    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)
        raise err


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=(LEFT | KICKED)))
async def left(event: ChatMemberUpdated, bot: Bot):
    logger.debug('MY event LEFT')
    try:
        logger.debug(event)
        chat = event.chat
        owner = event.from_user
        logger.info(f'Бот удален с канала {chat.id} {chat.title} пользователем {owner.username} {owner.id}')
    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)
        raise err


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR))
async def as_admin(event: ChatMemberUpdated, bot: Bot):
    logger.debug('MY event ADMINISTRATOR')
    try:
        chat = event.chat
        owner = event.from_user
        logger.info(f'Бот добавлен в канал {chat.id} {chat.title} как ADMINISTRATOR пользователем {owner.username} {owner.id}')
        # Добавляем канал в базу
        user = get_or_create_user(owner)
    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)
        raise err
