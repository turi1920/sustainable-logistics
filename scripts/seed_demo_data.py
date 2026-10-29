import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
import uuid

# Ensure project root is on sys.path so the script can be executed directly as `python scripts/seed_demo_data.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.security import get_password_hash
from backend.app.db.base import Base
from backend.app.db.session import async_session_factory, engine
from backend.app.models.authorization import AuthorizationPolicy, PartnerContract
from backend.app.models.identity import Facility, FacilityType, OrgType, Organization, User, UserRole
from backend.app.models.operations import RefundRecord, RefundStatus
from backend.app.models.returns import (
    ApprovalStatus,
    CustodyLocation,
    ProductCategory,
    RecoveryClassification,
    ReturnCaseStatus,
    ReturnItem,
    ReturnRequest,
)
from sqlalchemy import select


async def seed():
    clean_db = "--clean" in sys.argv or "--reseed" in sys.argv
    if clean_db:
        print("Cleaning existing database tables (--clean / --reseed requested)...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    else:
        print("Initializing database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        if not clean_db:
            stmt = select(Organization).where(Organization.code == "SRL_OPERATOR")
            existing_org = (await db.execute(stmt)).scalar_one_or_none()
            if existing_org:
                print("Database has already been seeded with initial demo data. All roles and records are ready.")
                print("\nDemo Credentials (password for all is 'password123'):")
                print("  Admin:       admin@reverse-logistics.com")
                print("  Agent:       agent@reverse-logistics.com")
                print("  Ops Spec:    ops@reverse-logistics.com")
                print("  Approver:    approver@apex.com")
                print("  Analyst:     analyst@reverse-logistics.com")
                print("\nTip: Pass --clean or --reseed to drop and re-create all demo records.")
                return

        print("Seeding organizations...")
        org_operator = Organization(
            code="SRL_OPERATOR",
            name="Sustainable Reverse Logistics Corp",
            org_type=OrgType.PLATFORM_OPERATOR,
            contact_email="admin@reverse-logistics.com"
        )
        org_apex = Organization(
            code="APEX_ELEC",
            name="Apex Electronics Inc.",
            org_type=OrgType.MANUFACTURER,
            contact_email="returns@apexelectronics.com"
        )
        org_nova = Organization(
            code="NOVA_COMP",
            name="Nova Computing Systems",
            org_type=OrgType.MANUFACTURER,
            contact_email="rma@novacomputing.com"
        )
        db.add_all([org_operator, org_apex, org_nova])
        await db.flush()

        print("Seeding users...")
        pw_hash = get_password_hash("password123")
        
        user_admin = User(
            organization_id=org_operator.id,
            email="admin@reverse-logistics.com",
            hashed_password=pw_hash,
            full_name="Alex Vance (Admin)",
            role=UserRole.PLATFORM_ADMIN
        )
        user_agent = User(
            organization_id=org_operator.id,
            email="agent@reverse-logistics.com",
            hashed_password=pw_hash,
            full_name="Sam Fisher (Field Agent)",
            role=UserRole.RETURN_AGENT
        )
        user_ops = User(
            organization_id=org_operator.id,
            email="ops@reverse-logistics.com",
            hashed_password=pw_hash,
            full_name="Elena Rostova (Operations Specialist)",
            role=UserRole.OPERATIONS_SPECIALIST
        )
        user_apex_approver = User(
            organization_id=org_apex.id,
            email="approver@apex.com",
            hashed_password=pw_hash,
            full_name="Marcus Brody (Apex Approver)",
            role=UserRole.MANUFACTURER_APPROVER
        )
        user_analyst = User(
            organization_id=org_operator.id,
            email="analyst@reverse-logistics.com",
            hashed_password=pw_hash,
            full_name="Sarah Connor (Finance & Sustainability)",
            role=UserRole.FINANCE_SUSTAINABILITY_ANALYST
        )
        db.add_all([user_admin, user_agent, user_ops, user_apex_approver, user_analyst])
        await db.flush()

        print("Seeding facilities...")
        facility = Facility(
            organization_id=org_operator.id,
            facility_code="FAC-CENTRAL-01",
            facility_name="Central Logistics & Refurb Depot",
            facility_type=FacilityType.CENTRAL_WAREHOUSE,
            address_line1="100 Circular Way",
            city="Fremont",
            postal_code="94538",
            country="US"
        )
        db.add(facility)

        print("Seeding partner contract & authorization policy for Apex...")
        contract = PartnerContract(
            manufacturer_org_id=org_apex.id,
            auto_return_on_timeout_authorized=True,
            contract_start_date=date(2026, 1, 1),
            contract_end_date=date(2027, 12, 31),
            default_return_shipping_carrier="UPS Ground"
        )
        policy = AuthorizationPolicy(
            manufacturer_org_id=org_apex.id,
            policy_code="APEX-LAPTOP-REPAIR-AUTO",
            description="Pre-approves repairs for Laptops where repair costs are under $150 and expected NRV is above $200",
            product_category=ProductCategory.LAPTOP,
            permitted_action=RecoveryClassification.REPAIR,
            max_repair_cost_threshold=Decimal("150.00"),
            min_expected_nrv_threshold=Decimal("200.00"),
            requires_safety_pass=True,
            valid_from=date(2026, 1, 1),
            valid_to=date(2027, 12, 31),
            is_active=True
        )
        db.add_all([contract, policy])
        await db.flush()

        print("Seeding sample return request...")
        sample_req = ReturnRequest(
            case_number="RET-20261030-1001",
            external_order_ref="ORD-AMZ-998811",
            customer_name="Jonathan Archer",
            customer_email="jarcher@example.com",
            customer_phone="555-0199",
            pickup_address="42 Warp Drive",
            pickup_city="San Francisco",
            pickup_postal_code="94107",
            status=ReturnCaseStatus.RETURN_REQUESTED,
            created_by_user_id=user_admin.id
        )
        db.add(sample_req)
        await db.flush()

        item_1 = ReturnItem(
            return_request_id=sample_req.id,
            manufacturer_org_id=org_apex.id,
            item_tag="TAG-APEX-8821",
            product_name="Apex UltraBook Pro 15",
            product_category=ProductCategory.LAPTOP,
            model_number="UB-15-2025",
            declared_serial_number="SN-APX-882199",
            return_reason="Display flickering intermittently",
            recovery_classification=RecoveryClassification.ON_HOLD,
            approval_status=ApprovalStatus.PENDING_APPROVAL,
            current_custody_location=CustodyLocation.WITH_RETURN_AGENT,
            requires_data_sanitization=True
        )
        db.add(item_1)

        refund = RefundRecord(
            return_request_id=sample_req.id,
            refund_amount=Decimal("1299.00"),
            status=RefundStatus.PENDING,
            manual_processing_notes="Customer eligible for full refund upon return verification."
        )
        db.add(refund)
        await db.commit()

        print("Database seeded successfully!")
        print("\nDemo Credentials:")
        print("  Admin:       admin@reverse-logistics.com / password123")
        print("  Agent:       agent@reverse-logistics.com / password123")
        print("  Ops Spec:    ops@reverse-logistics.com / password123")
        print("  Approver:    approver@apex.com / password123")
        print("  Analyst:     analyst@reverse-logistics.com / password123")


if __name__ == "__main__":
    asyncio.run(seed())
