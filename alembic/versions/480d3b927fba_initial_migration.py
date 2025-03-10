"""Initial migration

Revision ID: 480d3b927fba
Revises: 
Create Date: 2025-03-04 19:23:03.745909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '480d3b927fba'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS celery_schema")
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('telegram_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('chat_id', sa.String(length=255), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.Column('message_text', sa.String(length=255), nullable=False),
    sa.Column('interval', sa.Integer(), nullable=False),
    sa.Column('last_message_sent', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('chat_id')
    )
    op.create_table('celery_clockedschedule',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('clocked_time', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    schema='celery_schema',
    sqlite_autoincrement=True
    )
    op.create_table('celery_crontabschedule',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('minute', sa.String(length=240), nullable=False, comment='Cron Minutes to Run. Use "*" for "all". (Example: "0,30")'),
    sa.Column('hour', sa.String(length=96), nullable=False, comment='Cron Hours to Run. Use "*" for "all". (Example: "8,20")'),
    sa.Column('day_of_week', sa.String(length=64), nullable=False, comment='Cron Days Of The Week to Run. Use "*" for "all", Sunday is 0 or 7, Monday is 1. (Example: "0,5")'),
    sa.Column('day_of_month', sa.String(length=124), nullable=False, comment='Cron Days Of The Month to Run. Use "*" for "all". (Example: "1,15")'),
    sa.Column('month_of_year', sa.String(length=64), nullable=False, comment='Cron Months (1-12) Of The Year to Run. Use "*" for "all". (Example: "1,12")'),
    sa.Column('timezone', sa.String(length=64), nullable=False, comment='Timezone to Run the Cron Schedule on. Default is UTC.'),
    sa.PrimaryKeyConstraint('id'),
    schema='celery_schema',
    sqlite_autoincrement=True
    )
    op.create_table('celery_intervalschedule',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('every', sa.Integer(), nullable=False, comment='Number of interval periods to wait before running the task again'),
    sa.Column('period', sa.Enum('days', 'hours', 'minutes', 'seconds', 'microseconds', name='period'), nullable=False, comment='The type of period between task runs (Example: days)'),
    sa.CheckConstraint('every >= 1'),
    sa.PrimaryKeyConstraint('id'),
    schema='celery_schema',
    sqlite_autoincrement=True
    )
    op.create_table('celery_periodictask',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False, comment='Short Description For This Task'),
    sa.Column('task', sa.String(length=255), nullable=False, comment='The Name of the Celery Task that Should be Run.  (Example: "proj.tasks.import_contacts")'),
    sa.Column('args', sa.Text(), nullable=False, comment='JSON encoded positional arguments (Example: ["arg1", "arg2"])'),
    sa.Column('kwargs', sa.Text(), nullable=False, comment='JSON encoded keyword arguments (Example: {"argument": "value"})'),
    sa.Column('queue', sa.String(length=255), nullable=True, comment='Queue defined in CELERY_TASK_QUEUES. Leave None for default queuing.'),
    sa.Column('exchange', sa.String(length=255), nullable=True, comment='Override Exchange for low-level AMQP routing'),
    sa.Column('routing_key', sa.String(length=255), nullable=True, comment='Override Routing Key for low-level AMQP routing'),
    sa.Column('headers', sa.Text(), nullable=True, comment='JSON encoded message headers for the AMQP message.'),
    sa.Column('priority', sa.Integer(), nullable=True, comment='Priority Number between 0 and 255. Supported by: RabbitMQ, Redis (priority reversed, 0 is highest).'),
    sa.Column('expires', sa.DateTime(timezone=True), nullable=True, comment='Datetime after which the schedule will no longer trigger the task to run'),
    sa.Column('expire_seconds', sa.Integer(), nullable=True, comment='Timedelta with seconds which the schedule will no longer trigger the task to run'),
    sa.Column('one_off', sa.Boolean(), nullable=False, comment='If True, the schedule will only run the task a single time'),
    sa.Column('start_time', sa.DateTime(timezone=True), nullable=True, comment='Datetime when the schedule should begin triggering the task to run'),
    sa.Column('enabled', sa.Boolean(), nullable=False, comment='Set to False to disable the schedule'),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True, comment='Datetime that the schedule last triggered the task to run. '),
    sa.Column('total_run_count', sa.Integer(), nullable=False, comment='Running count of how many times the schedule has triggered the task'),
    sa.Column('date_changed', sa.DateTime(timezone=True), nullable=True, comment='Datetime that this PeriodicTask was last modified'),
    sa.Column('description', sa.Text(), nullable=True, comment='Detailed description about the details of this Periodic Task'),
    sa.Column('discriminator', sa.String(length=20), nullable=False, comment='Lower case name of the schedule class. '),
    sa.Column('schedule_id', sa.Integer(), nullable=False, comment='ID of the schedule model object. '),
    sa.CheckConstraint('priority BETWEEN 0 AND 255'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='celery_schema',
    sqlite_autoincrement=True
    )
    op.create_table('celery_periodictaskchanged',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('last_update', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='celery_schema',
    sqlite_autoincrement=False
    )
    op.create_table('celery_solarschedule',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('event', sa.Enum('dawn_astronomical', 'dawn_nautical', 'dawn_civil', 'sunrise', 'solar_noon', 'sunset', 'dusk_civil', 'dusk_nautical', 'dusk_astronomical', name='solarevent'), nullable=False, comment='The type of solar event when the job should run'),
    sa.Column('latitude', sa.Numeric(precision=9, scale=6, decimal_return_scale=6, asdecimal=False), nullable=False, comment='Run the task when the event happens at this latitude'),
    sa.Column('longitude', sa.Numeric(precision=9, scale=6, decimal_return_scale=6, asdecimal=False), nullable=False, comment='Run the task when the event happens at this longitude'),
    sa.CheckConstraint('latitude BETWEEN -90 AND 90'),
    sa.CheckConstraint('longitude BETWEEN -180 AND 180'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event', 'latitude', 'longitude'),
    schema='celery_schema',
    sqlite_autoincrement=True
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('celery_solarschedule', schema='celery_schema')
    op.drop_table('celery_periodictaskchanged', schema='celery_schema')
    op.drop_table('celery_periodictask', schema='celery_schema')
    op.drop_table('celery_intervalschedule', schema='celery_schema')
    op.drop_table('celery_crontabschedule', schema='celery_schema')
    op.drop_table('celery_clockedschedule', schema='celery_schema')
    op.drop_table('telegram_users')
    # ### end Alembic commands ###
