import asyncio
import datetime
import logging
from typing import Optional

from aiogram.types import Chat
from sqlalchemy import select, insert, update

from config_data.conf import LOGGING_CONFIG, conf, tz, get_my_loggers


from database.db import User, Session


logger, err_log = get_my_loggers()


def check_user(tg_id: int | str) -> User:
    """Возвращает найденного пользователя по tg_id"""
    logger.debug(f'Ищем юзера {tg_id}')
    with Session() as session:
        user: User = session.query(User).filter(User.tg_id == str(tg_id)).first()
        # logger.debug(f'Результат: {user}')
        return user


def get_or_create_user(user, refferal=None) -> Optional[User]:
    """Из юзера ТГ создает User"""
    try:
        old_user = check_user(user.id)
        if old_user:
            logger.debug(f'Пользователь {old_user} есть в базе')
            return old_user
        # Создание нового пользователя
        logger.debug('Добавляем пользователя')
        with Session() as session:
            new_user = User(tg_id=user.id,
                            first_name=user.first_name,
                            last_name=user.last_name,
                            full_name=user.full_name,
                            username=user.username,
                            register_date=datetime.datetime.now(tz=tz),
                            referral=refferal
                            )
            session.add(new_user)
            session.commit()
            logger.debug(f'Пользователь создан: {new_user}')
        return new_user
    except Exception as err:
        err_log.error('Пользователь не создан', exc_info=True)


if __name__ == '__main__':
    pass
