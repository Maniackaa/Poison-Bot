import datetime

from sqlalchemy import select

from config_data.conf import tz, get_my_loggers
from database.db import Session, User, Order, Case
from services.db_func import check_user

logger, err_log = get_my_loggers()

MAX_ORDERS_COUNT = 11


def get_or_create_case():
    """
    Если нет кейсов или в последнем кейсе более 11 заказов - возвращает новый.
    Иначе последний со статусом 1.
    :param order_id:
    :return:
    """
    logger.debug('get_or_create_case')
    try:
        session = Session()
        with session:
            last_case = select(Case).where(Case.status == 1).order_by(-Case.id)
            cases: list[Case] = session.execute(last_case).unique().scalars().all()
            logger.debug(f'Открытые cases: {cases}')
            if cases:
                case = cases[0]
                if case and len(case.orders) < MAX_ORDERS_COUNT:
                    logger.debug(f'case orders: {case.orders}')
                    return case
            # Если кейс не найден - создаем новый
            logger.debug('Создаем case')
            new_case = Case(created=datetime.datetime.now(tz=tz))
            session.add(new_case)
            session.commit()
            logger.debug(f'case создан: {new_case}')
            return new_case
    except Exception as err:
        raise err


def create_order(user: User, text, link):
    """Создание нового заказа"""
    session = Session(expire_on_commit=False)
    logger.debug(f'Создание нового заказа: {user}, {text}, {link}')
    with session:
        case = get_or_create_case()
        logger.debug(f'case для заказа: {case}. Заказы кейса: {case.orders}')
        new_order = Order(user_id=user.id,
                          text=text,
                          link=link,
                          case_id=case.id,
        )
        session.add(new_order)
        session.commit()
        logger.debug(f'Заказа создан: {new_order}')
        # Если case был с 10ю, то поменяем ему статус
        logger.debug(f'Было заказов в case: {len(case.orders)}')
        if len(case.orders) >= MAX_ORDERS_COUNT - 1:
            logger.debug(f'Закрываем case {case}')
            case.status = 2
            session.add(case)
            session.commit()
        return new_order


def get_active_case():
    """
    Возвращает активный кейс
    """
    logger.debug('get_or_create_case')
    try:
        session = Session()
        with session:
            cases = select(Case).order_by(-Case.id)
            last_case: Case = session.execute(cases).unique().scalars().first()
            logger.debug(f'Последний cases: {last_case}')
            return last_case
    except Exception as err:
        logger.error(err)


def get_case_text():
    logger.debug('Готовим текст.')
    case: Case = get_active_case()
    logger.debug(f'case: {case}')
    if case:
        orders_count = len(case.orders)
    else:
        orders_count = 0
    logger.debug(f'orders_count: {orders_count}')
    if orders_count >= MAX_ORDERS_COUNT:
        text = 'Заказ сформирован'
    else:
        text = 'Идет формирование заказа…\n\n'
    if orders_count > 0:
        text += f'<b>({MAX_ORDERS_COUNT})__</b>'
    else:
        text += f'{MAX_ORDERS_COUNT}___'
    for i in range(MAX_ORDERS_COUNT - 2):
        if i < orders_count - 1:
            text += f'<b>({MAX_ORDERS_COUNT - i - 1})___</b>'
        else:
            text += f'{MAX_ORDERS_COUNT - i - 1}___'
    if orders_count == MAX_ORDERS_COUNT:
        text += f'<b>(0)</b>'
    else:
        text += '1'

    text += f'\n\nОсталось <b>{MAX_ORDERS_COUNT - orders_count}</b> заказов\n\n'
    if case:
        for num, order in enumerate(case.orders, 1):
            user = order.user
            text += f'{num}. {user.username} {user.full_name} {order.link}\n'
    return text

# x = get_case_text()
# print(x)


def get_case_from_order(order: Order):
    session = Session()
    with session:
        order = select(Order).filter(Order.id == order.id)
        order = session.execute(order).unique().scalars().one_or_none()
        case = order.case
        logger.debug(case)
        return case


# my_case = get_or_create_case()
# print(my_case)
# user = check_user(585896156)
# print(user)
# for x in range(200):
#     my_order = create_order(user, 'text', 'link')
#     print(my_order)