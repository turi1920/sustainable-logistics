import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.config import settings
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models.authorization import AuthorizationPolicy, PartnerContract
from backend.app.models.identity import Facility, FacilityType, OrgType, Organization, User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def seed_data(db_session: AsyncSession):
    # Organizations
    operator_org = Organization(
        code="SRL_OPERATOR",
        name="Sustainable Reverse Logistics",
        org_type=OrgType.PLATFORM_OPERATOR,
        contact_email="admin@test.com"
    )
    mfg_org_1 = Organization(
        code="APEX",
        name="Apex Tech",
        org_type=OrgType.MANUFACTURER,
        contact_email="returns@apex.com"
    )
    mfg_org_2 = Organization(
        code="NOVA",
        name="Nova Devices",
        org_type=OrgType.MANUFACTURER,
        contact_email="returns@nova.com"
    )
    db_session.add_all([operator_org, mfg_org_1, mfg_org_2])
    await db_session.flush()

    # Users
    pw = get_password_hash("testpass123")
    admin_user = User(
        organization_id=operator_org.id,
        email="admin@test.com",
        hashed_password=pw,
        full_name="Platform Admin",
        role=UserRole.PLATFORM_ADMIN
    )
    agent_user = User(
        organization_id=operator_org.id,
        email="agent@test.com",
        hashed_password=pw,
        full_name="Return Agent",
        role=UserRole.RETURN_AGENT
    )
    ops_user = User(
        organization_id=operator_org.id,
        email="ops@test.com",
        hashed_password=pw,
        full_name="Ops Specialist",
        role=UserRole.OPERATIONS_SPECIALIST
    )
    mfg1_approver = User(
        organization_id=mfg_org_1.id,
        email="approver1@apex.com",
        hashed_password=pw,
        full_name="Apex Approver",
        role=UserRole.MANUFACTURER_APPROVER
    )
    mfg2_approver = User(
        organization_id=mfg_org_2.id,
        email="approver2@nova.com",
        hashed_password=pw,
        full_name="Nova Approver",
        role=UserRole.MANUFACTURER_APPROVER
    )
    analyst_user = User(
        organization_id=operator_org.id,
        email="analyst@test.com",
        hashed_password=pw,
        full_name="Finance Analyst",
        role=UserRole.FINANCE_SUSTAINABILITY_ANALYST
    )
    db_session.add_all([admin_user, agent_user, ops_user, mfg1_approver, mfg2_approver, analyst_user])

    # Facility
    facility = Facility(
        organization_id=operator_org.id,
        facility_code="FAC-TEST",
        facility_name="Central Test Hub",
        facility_type=FacilityType.CENTRAL_WAREHOUSE,
        address_line1="123 Test St",
        city="Testville",
        postal_code="12345"
    )
    db_session.add(facility)

    # Partner Contract for Apex
    contract_apex = PartnerContract(
        manufacturer_org_id=mfg_org_1.id,
        auto_return_on_timeout_authorized=True,
        contract_start_date=date(2026, 1, 1),
        contract_end_date=date(2027, 12, 31)
    )
    # Partner Contract for Nova (No auto return)
    contract_nova = PartnerContract(
        manufacturer_org_id=mfg_org_2.id,
        auto_return_on_timeout_authorized=False,
        contract_start_date=date(2026, 1, 1),
        contract_end_date=date(2027, 12, 31)
    )
    db_session.add_all([contract_apex, contract_nova])

    await db_session.commit()

    return {
        "org_operator": operator_org,
        "org_apex": mfg_org_1,
        "org_nova": mfg_org_2,
        "admin": admin_user,
        "agent": agent_user,
        "ops": ops_user,
        "mfg1_approver": mfg1_approver,
        "mfg2_approver": mfg2_approver,
        "analyst": analyst_user,
        "facility": facility,
        # Tokens
        "admin_token": create_access_token(str(admin_user.id), {"role": admin_user.role.value, "org_id": str(operator_org.id)}),
        "agent_token": create_access_token(str(agent_user.id), {"role": agent_user.role.value, "org_id": str(operator_org.id)}),
        "ops_token": create_access_token(str(ops_user.id), {"role": ops_user.role.value, "org_id": str(operator_org.id)}),
        "mfg1_token": create_access_token(str(mfg1_approver.id), {"role": mfg1_approver.role.value, "org_id": str(mfg_org_1.id)}),
        "mfg2_token": create_access_token(str(mfg2_approver.id), {"role": mfg2_approver.role.value, "org_id": str(mfg_org_2.id)}),
        "analyst_token": create_access_token(str(analyst_user.id), {"role": analyst_user.role.value, "org_id": str(operator_org.id)}),
    }
