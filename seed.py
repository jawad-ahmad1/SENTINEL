import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
import sys
sys.path.append('d:/attendance_system')
from app.models.employee import Employee
from app.db.session import engine, async_session_factory

async def seed():
    async with async_session_factory() as session:
        employees = [
            Employee(first_name='Sarah', last_name='Jenkins', rfid_uid='CC8899AA', email='s.jenkins@sentinel.com', department='Engineering', position='Senior Developer', phone='+15550101'),
            Employee(first_name='David', last_name='Chen', rfid_uid='BB776655', email='d.chen@sentinel.com', department='Operations', position='Operations Manager', phone='+15550102'),
            Employee(first_name='Emily', last_name='Roberts', rfid_uid='AA554433', email='e.roberts@sentinel.com', department='HR', position='HR Specialist', phone='+15550103'),
        ]
        session.add_all(employees)
        await session.commit()
        print('Fake employees seeded via DB!')

asyncio.run(seed())
