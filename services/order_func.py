import datetime

from sqlalchemy import select

from config_data.conf import tz, get_my_loggers
from database.db import Session, User, Order, Case
from services.db_func import check_user
from lexicon.lexicon import ORDER_SUCCESS_TEMPLATE

logger, err_log = get_my_loggers()


def create_order(user: User, text: str, link: str) -> Order:
    """
    Создание нового заказа. Каждый заказ сразу идёт в работу (1 заказ = 1 кейс).
    """
    session = Session(expire_on_commit=False)
    logger.debug(f'Создание нового заказа: {user}, {text}, {link}')
    with session:
        new_case = Case(created=datetime.datetime.now(tz=tz), status=2)  # status=2 — сразу сформирован
        session.add(new_case)
        session.flush()
        new_order = Order(user_id=user.id, text=text, link=link, case_id=new_case.id)
        session.add(new_order)
        session.commit()
        logger.debug(f'Заказ создан: {new_order}')
        return new_order


def get_order_text(user: User, order: Order) -> str:
    """Текст для сообщения о заказе (в группу и пользователю)."""
    first_name = user.first_name or user.username or 'пользователь'
    username = user.username or '—'
    return ORDER_SUCCESS_TEMPLATE.format(
        first_name=first_name,
        username=username,
        link=order.link,
    )


def get_case_from_order(order: Order) -> Case | None:
    session = Session()
    with session:
        result = session.execute(select(Order).filter(Order.id == order.id))
        order_obj = result.unique().scalars().one_or_none()
        return order_obj.case if order_obj else None


def get_case_from_order_id(order_id: int) -> Case | None:
    session = Session()
    logger.debug(f'Ищем case по order_id {order_id}')
    with session:
        result = session.execute(select(Order).filter(Order.id == order_id))
        order = result.unique().scalars().one_or_none()
        if order:
            logger.debug(f'order: {order}')
            case = order.case
            logger.debug(f'case: {case}. case.msg_id: {case.msg_id}')
            return case
        return None


def get_my_orders(tg_id: int | str) -> list[Order]:
    user: User | None = check_user(tg_id)
    return user.orders if user else []


def delete_order(order_id: int) -> bool:
    """Удаление заказа. Возвращает True если удалён."""
    try:
        logger.debug(f'Удаление заказа {order_id}')
        session = Session()
        with session:
            result = session.execute(select(Order).filter(Order.id == order_id))
            order = result.unique().scalars().one_or_none()
            if order:
                logger.debug(f'Заказ найден: {order}')
                session.delete(order)
                session.commit()
                logger.debug('Заказ удален')
                return True
            return False
    except Exception as err:
        logger.error(f'Ошибка при удалении заказа: {err}')
        return False


# my_case = get_or_create_case()
# print(my_case)
# user = check_user(585896156)
# print(user)
# for x in range(200):
#     my_order = create_order(user, 'text', 'link')
#     print(my_order)