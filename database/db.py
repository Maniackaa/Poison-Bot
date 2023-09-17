import datetime
import uuid

from time import time

from sqlalchemy import create_engine, ForeignKey, Date, String, DateTime, \
    Float, UniqueConstraint, Integer, MetaData, BigInteger, ARRAY, Table, Column
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import sessionmaker

from config_data.conf import conf, tz, get_my_loggers, BASE_DIR

logger, err_log = get_my_loggers()
metadata = MetaData()
db_url = f"postgresql+psycopg2://{conf.db.db_user}:{conf.db.db_password}@{conf.db.db_host}:{conf.db.db_port}/{conf.db.database}"
# engine = create_engine(db_url, echo=False, max_overflow=-1)
engine = create_engine(db_url, echo=False)

# db_path = BASE_DIR / 'db.sqlite3'
# engine = create_engine(f"sqlite:///{db_path}", echo=False)

Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    tg_id: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str] = mapped_column(String(50), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=True)
    register_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    referral: Mapped[str] = mapped_column(String(20), nullable=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="user", lazy='joined')

    def __repr__(self):
        return f'{self.id}. {self.tg_id} {self.username or "-"}'


class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    created: Mapped[time] = mapped_column(DateTime(timezone=True), default=lambda: datetime.datetime.now(tz=tz))
    case_id: Mapped[int] = mapped_column(ForeignKey('cases.id', ondelete='SET NULL'))
    text: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(100))
    msg_link: Mapped[str] = mapped_column(String(100), nullable=True)
    case: Mapped["Case"] = relationship(back_populates="orders", lazy='subquery')
    user: Mapped["User"] = relationship(back_populates="orders", lazy='joined')

    def __repr__(self):
        return f'{self.id}. {self.link}'


class Case(Base):
    __tablename__ = 'cases'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created: Mapped[time] = mapped_column(DateTime(timezone=True))
    closed: Mapped[time] = mapped_column(DateTime(timezone=True), nullable=True)
    msg_id: Mapped[int] = mapped_column(Integer(), nullable=True)
    status: Mapped[int] = mapped_column(Integer(), comment='1 - открыт, 2 - закрыт', default=1)
    orders: Mapped[list["Order"]] = relationship(back_populates="case", lazy='joined')

    def __repr__(self):
        return f'Case {self.id}. {self.created} status: {self.status} '

    def set(self, key, value):
        _session = Session()
        try:
            with _session:
                order = _session.query(Case).filter(Case.id == self.id).one_or_none()
                setattr(order, key, value)
                _session.commit()
                logger.debug(f'Изменено значение {key} на {value}')
        except Exception as err:
            err_log.error(f'Ошибка изменения {key} на {value}')
            raise err



Base.metadata.create_all(engine)
