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

from sqlalchemy import select
from backend.app.core.security import get_password_hash
from backend.app.db.base import Base
from backend.app.db.session import async_session_factory, engine
from backend.app.models.assessment import (
    AssessmentReport,
    EnclosureCondition,
    Inspection,
    RecoveryEstimate,
    ScreenCondition,
)
from backend.app.models.authorization import (
    ApprovalRequest,
    ApprovalRequestItem,
    AuthorizationDecision,
    AuthorizationPolicy,
    DecisionPath,
    PartnerContract,
)
from backend.app.models.execution import (
    AuthorizedDisposition,
    PartsUsage,
    RecoveryWorkOrder,
    ReleaseAuthorization,
    SanitizationMethod,
    SanitizationRecord,
    SanitizationStatus,
    WorkOrderStatus,
)
from backend.app.models.identity import Facility, FacilityType, OrgType, Organization, User, UserRole
from backend.app.models.logistics import CustodyEvent, CustodyEventType, WarehouseReceipt
from backend.app.models.operations import AuditEvent, NotificationLog, RefundRecord, RefundStatus
from backend.app.models.returns import (
    ApprovalStatus,
    CustodyLocation,
    DamageClassification,
    PickupAssignment,
    ProductCategory,
    RecoveryClassification,
    ReturnCaseStatus,
    ReturnItem,
    ReturnRequest,
    VerificationOutcome,
)


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
                print("  Approver (Apex): approver@apex.com")
                print("  Approver (Nova): approver@nova.com")
                print("  Analyst:     analyst@reverse-logistics.com")
                print("  Technician:  tech@reverse-logistics.com")
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

        print("Seeding users across all roles...")
        pw_hash = get_password_hash("password123")
        
        user_admin = User(
            organization_id=org_operator.id,
            email="admin@reverse-logistics.com",
            hashed_password=pw_hash,
            full_name="Alex Vance (Platform Admin)",
            role=UserRole.PLATFORM_ADMIN
        )
        user_agent = User(
            organization_id=org_operator.id,
            email="agent@reverse-logistics.com",
            hashed_password=pw_hash,
            full_name="Sam Fisher (Return Agent)",
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
        user_nova_approver = User(
            organization_id=org_nova.id,
            email="approver@nova.com",
            hashed_password=pw_hash,
            full_name="Tali'Zorah (Nova Approver)",
            role=UserRole.MANUFACTURER_APPROVER
        )
        user_analyst = User(
            organization_id=org_operator.id,
            email="analyst@reverse-logistics.com",
            hashed_password=pw_hash,
            full_name="Sarah Connor (Finance & Sustainability)",
            role=UserRole.FINANCE_SUSTAINABILITY_ANALYST
        )
        user_tech = User(
            organization_id=org_operator.id,
            email="tech@reverse-logistics.com",
            hashed_password=pw_hash,
            full_name="Jax Briggs (Recovery Technician)",
            role=UserRole.OPERATIONS_SPECIALIST
        )
        db.add_all([user_admin, user_agent, user_ops, user_apex_approver, user_nova_approver, user_analyst, user_tech])
        await db.flush()

        print("Seeding facilities...")
        facility_central = Facility(
            organization_id=org_operator.id,
            facility_code="FAC-CENTRAL-01",
            facility_name="Central Logistics & Refurb Depot",
            facility_type=FacilityType.CENTRAL_WAREHOUSE,
            address_line1="100 Circular Way",
            city="Fremont",
            postal_code="94538",
            country="US"
        )
        facility_east = Facility(
            organization_id=org_operator.id,
            facility_code="FAC-EAST-02",
            facility_name="East Coast Recovery Hub",
            facility_type=FacilityType.REPAIR_DEPOT,
            address_line1="500 Green Terminal Blvd",
            city="Newark",
            postal_code="07114",
            country="US"
        )
        db.add_all([facility_central, facility_east])
        await db.flush()

        print("Seeding partner contracts & policies...")
        contract_apex = PartnerContract(
            manufacturer_org_id=org_apex.id,
            auto_return_on_timeout_authorized=True,
            contract_start_date=date(2026, 1, 1),
            contract_end_date=date(2027, 12, 31),
            default_return_shipping_carrier="UPS Ground"
        )
        contract_nova = PartnerContract(
            manufacturer_org_id=org_nova.id,
            auto_return_on_timeout_authorized=False,
            contract_start_date=date(2026, 1, 1),
            contract_end_date=date(2027, 12, 31),
            default_return_shipping_carrier="FedEx Freight"
        )
        policy_apex = AuthorizationPolicy(
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
        policy_nova = AuthorizationPolicy(
            manufacturer_org_id=org_nova.id,
            policy_code="NOVA-PHONE-REPAIR-AUTO",
            description="Pre-approves smartphone repairs under $90 repair cost with expected NRV > $150",
            product_category=ProductCategory.SMARTPHONE,
            permitted_action=RecoveryClassification.REPAIR,
            max_repair_cost_threshold=Decimal("90.00"),
            min_expected_nrv_threshold=Decimal("150.00"),
            requires_safety_pass=True,
            valid_from=date(2026, 1, 1),
            valid_to=date(2027, 12, 31),
            is_active=True
        )
        db.add_all([contract_apex, contract_nova, policy_apex, policy_nova])
        await db.flush()

        print("Seeding rich return cases across all lifecycle stages...")
        now_utc = datetime.now(timezone.utc)

        # -------------------------------------------------------------------
        # CASE 1: RETURN_REQUESTED (Customer Premises, awaiting pickup assignment)
        # -------------------------------------------------------------------
        req1 = ReturnRequest(
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
        db.add(req1)
        await db.flush()

        item1 = ReturnItem(
            return_request_id=req1.id,
            manufacturer_org_id=org_apex.id,
            item_tag="TAG-APEX-8821",
            product_name="Apex UltraBook Pro 15",
            product_category=ProductCategory.LAPTOP,
            model_number="UB-15-2025",
            declared_serial_number="SN-APX-882199",
            return_reason="Display flickering intermittently",
            recovery_classification=RecoveryClassification.ON_HOLD,
            approval_status=ApprovalStatus.NOT_REQUIRED_POLICY_AUTHORIZED,
            current_custody_location=CustodyLocation.WITH_RETURN_AGENT,
            requires_data_sanitization=True
        )
        refund1 = RefundRecord(
            return_request_id=req1.id,
            refund_amount=Decimal("1299.00"),
            status=RefundStatus.PENDING,
            manual_processing_notes="Full refund upon field pickup verification."
        )
        db.add_all([item1, refund1])

        # -------------------------------------------------------------------
        # CASE 2: PICKUP_ASSIGNED (Assigned to Return Agent Sam Fisher)
        # -------------------------------------------------------------------
        req2 = ReturnRequest(
            case_number="RET-20261030-1002",
            external_order_ref="ORD-BBY-2026-4412",
            customer_name="Elena Fisher",
            customer_email="elena.fisher@example.com",
            customer_phone="555-0244",
            pickup_address="742 Evergreen Terrace",
            pickup_city="Springfield",
            pickup_postal_code="97477",
            status=ReturnCaseStatus.PICKUP_ASSIGNED,
            created_by_user_id=user_admin.id
        )
        db.add(req2)
        await db.flush()

        item2 = ReturnItem(
            return_request_id=req2.id,
            manufacturer_org_id=org_nova.id,
            item_tag="TAG-NOVA-1044",
            product_name="Nova Phone X Pro",
            product_category=ProductCategory.SMARTPHONE,
            model_number="NPX-256-BLK",
            declared_serial_number="SN-NOV-441299",
            return_reason="Microphone distorted during calls",
            recovery_classification=RecoveryClassification.ON_HOLD,
            approval_status=ApprovalStatus.NOT_REQUIRED_POLICY_AUTHORIZED,
            current_custody_location=CustodyLocation.WITH_RETURN_AGENT,
            requires_data_sanitization=True
        )
        db.add(item2)
        await db.flush()

        pickup2 = PickupAssignment(
            return_item_id=item2.id,
            agent_user_id=user_agent.id,
            scheduled_date=date.today(),
            initial_damage=DamageClassification.LOW,
            verification_outcome=VerificationOutcome.VERIFIED,
            verification_notes="Observed serial SN-NOV-441299 matches box. Outer chassis pristine."
        )
        refund2 = RefundRecord(
            return_request_id=req2.id,
            refund_amount=Decimal("899.00"),
            status=RefundStatus.PENDING,
            manual_processing_notes="Pending warehouse arrival scan."
        )
        db.add_all([pickup2, refund2])

        # -------------------------------------------------------------------
        # CASE 3: WAREHOUSE_RECEIVED (In storage bin at Central Depot)
        # -------------------------------------------------------------------
        req3 = ReturnRequest(
            case_number="RET-20261030-1003",
            external_order_ref="ORD-TGT-5519-88",
            customer_name="Marcus Wright",
            customer_email="mwright@example.com",
            customer_phone="555-0377",
            pickup_address="10 Cyber Lane",
            pickup_city="Fremont",
            pickup_postal_code="94538",
            status=ReturnCaseStatus.WAREHOUSE_RECEIVED,
            created_by_user_id=user_admin.id
        )
        db.add(req3)
        await db.flush()

        item3 = ReturnItem(
            return_request_id=req3.id,
            manufacturer_org_id=org_apex.id,
            item_tag="TAG-APEX-3310",
            product_name="Apex Studio ANC Headphones",
            product_category=ProductCategory.AUDIO,
            model_number="HP-ANC-PRO",
            declared_serial_number="SN-APX-331088",
            verified_serial_number="SN-APX-331088",
            return_reason="Left earcup cushion loose; sound is fully functional",
            recovery_classification=RecoveryClassification.ON_HOLD,
            approval_status=ApprovalStatus.NOT_REQUIRED_POLICY_AUTHORIZED,
            current_custody_location=CustodyLocation.WAREHOUSE,
            current_facility_id=facility_central.id,
            requires_data_sanitization=False
        )
        db.add(item3)
        await db.flush()

        receipt3 = WarehouseReceipt(
            return_item_id=item3.id,
            facility_id=facility_central.id,
            receiver_user_id=user_ops.id,
            intake_barcode="INTAKE-BAR-3310-01",
            storage_bin="BIN-A1-04",
            packaging_intact=True,
            intake_notes="Scanned at Central Depot dock 2. Assigned to storage bin A1-04."
        )
        custody_evt3 = CustodyEvent(
            return_item_id=item3.id,
            actor_user_id=user_ops.id,
            event_type=CustodyEventType.WAREHOUSE_ARRIVAL,
            from_location="IN_TRANSIT",
            to_location="WAREHOUSE",
            notes="Received at Central Depot dock 2; allocated to storage bin BIN-A1-04"
        )
        refund3 = RefundRecord(
            return_request_id=req3.id,
            refund_amount=Decimal("249.00"),
            status=RefundStatus.INITIATED,
            initiated_at=now_utc - timedelta(hours=3),
            manual_processing_notes="Refund initiated following warehouse intake confirmation."
        )
        db.add_all([receipt3, custody_evt3, refund3])

        # -------------------------------------------------------------------
        # CASE 4: ASSESSED (Path A Pre-Authorized Repair)
        # -------------------------------------------------------------------
        req4 = ReturnRequest(
            case_number="RET-20261030-1004",
            external_order_ref="ORD-APX-7761-02",
            customer_name="Chloe Frazer",
            customer_email="cfrazer@example.com",
            customer_phone="555-0488",
            pickup_address="88 Explorers Way",
            pickup_city="Oakland",
            pickup_postal_code="94607",
            status=ReturnCaseStatus.ASSESSED,
            created_by_user_id=user_admin.id
        )
        db.add(req4)
        await db.flush()

        item4 = ReturnItem(
            return_request_id=req4.id,
            manufacturer_org_id=org_apex.id,
            item_tag="TAG-APEX-4902",
            product_name="Apex UltraBook Slim 13",
            product_category=ProductCategory.LAPTOP,
            model_number="UBS-13-2025",
            declared_serial_number="SN-APX-490211",
            verified_serial_number="SN-APX-490211",
            return_reason="Damaged USB-C charging daughterboard",
            recovery_classification=RecoveryClassification.REPAIR,
            approval_status=ApprovalStatus.APPROVED,
            current_custody_location=CustodyLocation.INSPECTION_FACILITY,
            current_facility_id=facility_central.id,
            requires_data_sanitization=True
        )
        db.add(item4)
        await db.flush()

        insp4 = Inspection(
            return_item_id=item4.id,
            inspector_user_id=user_ops.id,
            is_functional=True,
            powers_on=True,
            screen_condition=ScreenCondition.PRISTINE,
            enclosure_condition=EnclosureCondition.GRADE_A_MINT,
            battery_health_pct=94,
            has_safety_hazard=False,
            technician_notes="Motherboard and display pristine. USB-C port daughterboard replacement required."
        )
        db.add(insp4)
        await db.flush()

        est4_repair = RecoveryEstimate(
            inspection_id=insp4.id,
            option_type=RecoveryClassification.REPAIR,
            is_technically_eligible=True,
            expected_resale_value=Decimal("480.00"),
            parts_cost=Decimal("60.00"),
            labour_cost=Decimal("50.00"),
            packaging_cost=Decimal("15.00"),
            transportation_cost=Decimal("25.00"),
            sanitization_cost=Decimal("20.00"),
            net_recovery_value=Decimal("310.00")
        )
        report4 = AssessmentReport(
            return_item_id=item4.id,
            recommended_option=RecoveryClassification.REPAIR,
            recommendation_rationale="Repair provides highest Net Recovery Value ($310.00) and meets Path A pre-authorization thresholds.",
            calculation_snapshot={"REPAIR": {"nrv": 310.00, "resale": 480.00, "cost": 170.00}},
            approval_deadline=now_utc + timedelta(days=5)
        )
        refund4 = RefundRecord(
            return_request_id=req4.id,
            refund_amount=Decimal("1099.00"),
            status=RefundStatus.PROCESSING,
            initiated_at=now_utc - timedelta(hours=6),
            manual_processing_notes="Refund batch queued in financial disbursement ledger."
        )
        db.add_all([est4_repair, report4, refund4])

        # -------------------------------------------------------------------
        # CASE 5: ASSESSED (Path B Pending Review for Nova Approver)
        # -------------------------------------------------------------------
        req5 = ReturnRequest(
            case_number="RET-20261030-1005",
            external_order_ref="ORD-NOV-9901-44",
            customer_name="David Sarif",
            customer_email="dsarif@example.com",
            customer_phone="555-0566",
            pickup_address="200 Detroit Tech Park",
            pickup_city="Detroit",
            pickup_postal_code="48201",
            status=ReturnCaseStatus.ASSESSED,
            created_by_user_id=user_admin.id
        )
        db.add(req5)
        await db.flush()

        item5 = ReturnItem(
            return_request_id=req5.id,
            manufacturer_org_id=org_nova.id,
            item_tag="TAG-NOVA-8840",
            product_name="Nova Workstation Blade 16",
            product_category=ProductCategory.LAPTOP,
            model_number="NWB-16-CAD",
            declared_serial_number="SN-NOV-884012",
            verified_serial_number="SN-NOV-884012",
            return_reason="Thermal throttling under heavy CAD load",
            recovery_classification=RecoveryClassification.REPAIR,
            approval_status=ApprovalStatus.PENDING_APPROVAL,
            current_custody_location=CustodyLocation.WAREHOUSE,
            current_facility_id=facility_central.id,
            requires_data_sanitization=True
        )
        db.add(item5)
        await db.flush()

        insp5 = Inspection(
            return_item_id=item5.id,
            inspector_user_id=user_ops.id,
            is_functional=True,
            powers_on=True,
            screen_condition=ScreenCondition.PRISTINE,
            enclosure_condition=EnclosureCondition.GRADE_B_LIGHT_WEAR,
            battery_health_pct=91,
            has_safety_hazard=False,
            technician_notes="Dual cooling fan bearing seized. Vapour chamber assembly replacement required ($220 parts + labor). Exceeds auto-approval limit."
        )
        db.add(insp5)
        await db.flush()

        est5 = RecoveryEstimate(
            inspection_id=insp5.id,
            option_type=RecoveryClassification.REPAIR,
            is_technically_eligible=True,
            expected_resale_value=Decimal("1450.00"),
            parts_cost=Decimal("140.00"),
            labour_cost=Decimal("80.00"),
            packaging_cost=Decimal("25.00"),
            transportation_cost=Decimal("35.00"),
            sanitization_cost=Decimal("30.00"),
            net_recovery_value=Decimal("1140.00")
        )
        report5 = AssessmentReport(
            return_item_id=item5.id,
            recommended_option=RecoveryClassification.REPAIR,
            recommendation_rationale="High-value workstation with $1,140.00 projected NRV. Requires human authorization because repair cost ($220.00) exceeds auto-policy limit.",
            calculation_snapshot={"REPAIR": {"nrv": 1140.00, "resale": 1450.00, "cost": 310.00}},
            approval_deadline=now_utc + timedelta(days=4, hours=18)
        )
        db.add_all([est5, report5])
        await db.flush()

        app_req5 = ApprovalRequest(
            manufacturer_org_id=org_nova.id,
            batch_reference="BATCH-NOV-2026-001",
            deadline_at=now_utc + timedelta(days=4, hours=18),
            is_closed=False
        )
        db.add(app_req5)
        await db.flush()

        app_req_item5 = ApprovalRequestItem(
            approval_request_id=app_req5.id,
            return_item_id=item5.id,
            assessment_report_id=report5.id,
            is_decided=False
        )
        refund5 = RefundRecord(
            return_request_id=req5.id,
            refund_amount=Decimal("1850.00"),
            status=RefundStatus.INITIATED,
            initiated_at=now_utc - timedelta(hours=12),
            manual_processing_notes="Refund initiated while manufacturer reviews recovery authorization."
        )
        db.add_all([app_req_item5, refund5])

        # -------------------------------------------------------------------
        # CASE 6: ASSESSED - Safety Blocker (Swollen Lithium Battery -> Recycling)
        # -------------------------------------------------------------------
        req6 = ReturnRequest(
            case_number="RET-20261030-1006",
            external_order_ref="ORD-WMT-3321-77",
            customer_name="Sarah Walker",
            customer_email="swalker@example.com",
            customer_phone="555-0677",
            pickup_address="404 Hazard Street",
            pickup_city="San Jose",
            pickup_postal_code="95112",
            status=ReturnCaseStatus.ASSESSED,
            created_by_user_id=user_admin.id
        )
        db.add(req6)
        await db.flush()

        item6 = ReturnItem(
            return_request_id=req6.id,
            manufacturer_org_id=org_apex.id,
            item_tag="TAG-APEX-9905",
            product_name="Apex PowerTablet 10",
            product_category=ProductCategory.TABLET,
            model_number="TAB-PWR-10",
            declared_serial_number="SN-APX-990577",
            verified_serial_number="SN-APX-990577",
            return_reason="Back cover popped open, pungent metallic smell",
            recovery_classification=RecoveryClassification.RECYCLING,
            approval_status=ApprovalStatus.APPROVED,
            current_custody_location=CustodyLocation.WAREHOUSE,
            current_facility_id=facility_central.id,
            requires_data_sanitization=False
        )
        db.add(item6)
        await db.flush()

        insp6 = Inspection(
            return_item_id=item6.id,
            inspector_user_id=user_ops.id,
            is_functional=False,
            powers_on=False,
            screen_condition=ScreenCondition.CRACKED,
            enclosure_condition=EnclosureCondition.STRUCTURAL_DAMAGE,
            has_safety_hazard=True,
            safety_hazard_details="Severe lithium-polymer pouch cell swelling with structural enclosure rupture. High fire risk. All resale and repair routes blocked.",
            technician_notes="Critical safety risk: device quarantined immediately in fire-suppression disposal bin."
        )
        db.add(insp6)
        await db.flush()

        est6_recycle = RecoveryEstimate(
            inspection_id=insp6.id,
            option_type=RecoveryClassification.RECYCLING,
            is_technically_eligible=True,
            expected_resale_value=Decimal("0.00"),
            parts_cost=Decimal("0.00"),
            labour_cost=Decimal("15.00"),
            packaging_cost=Decimal("5.00"),
            transportation_cost=Decimal("10.00"),
            sanitization_cost=Decimal("0.00"),
            net_recovery_value=Decimal("-30.00")
        )
        report6 = AssessmentReport(
            return_item_id=item6.id,
            recommended_option=RecoveryClassification.RECYCLING,
            recommendation_rationale="Lithium battery puncture hazard forces immediate certified recycling disposal. Resale strictly prohibited under safety policy.",
            calculation_snapshot={"RECYCLING": {"nrv": -30.00, "safety_blocker": True}},
            approval_deadline=now_utc + timedelta(days=1)
        )
        refund6 = RefundRecord(
            return_request_id=req6.id,
            refund_amount=Decimal("499.00"),
            status=RefundStatus.PROCESSING,
            initiated_at=now_utc - timedelta(hours=8),
            manual_processing_notes="Full safety refund granted to customer immediately."
        )
        db.add_all([est6_recycle, report6, refund6])

        # -------------------------------------------------------------------
        # CASE 7: RECOVERY_IN_PROGRESS (Technician Work Order & Sanitization Active)
        # -------------------------------------------------------------------
        req7 = ReturnRequest(
            case_number="RET-20261030-1007",
            external_order_ref="ORD-AMZ-6612-90",
            customer_name="Garrus Vakarian",
            customer_email="gvakarian@example.com",
            customer_phone="555-0788",
            pickup_address="500 Citadel Plaza",
            pickup_city="Palo Alto",
            pickup_postal_code="94301",
            status=ReturnCaseStatus.RECOVERY_IN_PROGRESS,
            created_by_user_id=user_admin.id
        )
        db.add(req7)
        await db.flush()

        item7 = ReturnItem(
            return_request_id=req7.id,
            manufacturer_org_id=org_nova.id,
            item_tag="TAG-NOVA-5511",
            product_name="Nova Slate Pro 12",
            product_category=ProductCategory.TABLET,
            model_number="NSP-12-LTE",
            declared_serial_number="SN-NOV-551100",
            verified_serial_number="SN-NOV-551100",
            return_reason="Customer buyer remorse within 14 days",
            recovery_classification=RecoveryClassification.REFURBISHMENT,
            approval_status=ApprovalStatus.APPROVED,
            current_custody_location=CustodyLocation.REPAIR_FACILITY,
            current_facility_id=facility_central.id,
            requires_data_sanitization=True
        )
        db.add(item7)
        await db.flush()

        wo7 = RecoveryWorkOrder(
            return_item_id=item7.id,
            facility_id=facility_central.id,
            assigned_technician_id=user_tech.id,
            work_order_type=RecoveryClassification.REFURBISHMENT,
            status=WorkOrderStatus.IN_PROGRESS,
            actual_parts_cost=Decimal("35.00"),
            actual_labour_cost=Decimal("40.00"),
            actual_packaging_cost=Decimal("12.00"),
            work_summary="Refurbishing housing and replacing screen protector gasket. Sanitization pass 2 of 3 executing.",
            started_at=now_utc - timedelta(hours=2)
        )
        db.add(wo7)
        await db.flush()

        part7 = PartsUsage(
            work_order_id=wo7.id,
            part_number="GSK-NSP12-SEAL",
            part_description="Nova Slate Pro 12 OEM Waterproof Bezel Gasket",
            quantity=1,
            unit_cost=Decimal("35.00")
        )
        san7 = SanitizationRecord(
            return_item_id=item7.id,
            technician_user_id=user_tech.id,
            sanitization_status=SanitizationStatus.IN_PROGRESS,
            method=SanitizationMethod.NIST_800_88_CLEAR,
            verification_tool="Blancco File Eraser v7.1",
            started_at=now_utc - timedelta(hours=1)
        )
        refund7 = RefundRecord(
            return_request_id=req7.id,
            refund_amount=Decimal("650.00"),
            status=RefundStatus.PROCESSING,
            initiated_at=now_utc - timedelta(hours=5),
            manual_processing_notes="Disbursement batch queued."
        )
        db.add_all([part7, san7, refund7])

        # -------------------------------------------------------------------
        # CASE 8: COMPLETED / RELEASED (NIST 800-88 Passed & Resale Released)
        # -------------------------------------------------------------------
        req8 = ReturnRequest(
            case_number="RET-20261030-1008",
            external_order_ref="ORD-APX-1122-33",
            customer_name="Liara T'Soni",
            customer_email="ltsoni@example.com",
            customer_phone="555-0899",
            pickup_address="100 Thessia Way",
            pickup_city="Berkeley",
            pickup_postal_code="94720",
            status=ReturnCaseStatus.COMPLETED,
            created_by_user_id=user_admin.id
        )
        db.add(req8)
        await db.flush()

        item8 = ReturnItem(
            return_request_id=req8.id,
            manufacturer_org_id=org_apex.id,
            item_tag="TAG-APEX-7744",
            product_name="Apex Edge Phone 14",
            product_category=ProductCategory.SMARTPHONE,
            model_number="AEP-14-PRO",
            declared_serial_number="SN-APX-774421",
            verified_serial_number="SN-APX-774421",
            return_reason="Unwanted gift; unopened box and accessories",
            recovery_classification=RecoveryClassification.RESALE_AS_NEW_ELIGIBLE,
            approval_status=ApprovalStatus.NOT_REQUIRED_POLICY_AUTHORIZED,
            current_custody_location=CustodyLocation.WAREHOUSE,
            current_facility_id=facility_central.id,
            requires_data_sanitization=True
        )
        db.add(item8)
        await db.flush()

        san8 = SanitizationRecord(
            return_item_id=item8.id,
            technician_user_id=user_tech.id,
            sanitization_status=SanitizationStatus.PASSED,
            method=SanitizationMethod.NIST_800_88_PURGE,
            verification_tool="NIST SP 800-88 Cryptographic Firmware Wipe Tool v4.2",
            certificate_ref="CERT-NIST-APX-7744-PURGE",
            started_at=now_utc - timedelta(hours=10),
            completed_at=now_utc - timedelta(hours=9),
            verified_at=now_utc - timedelta(hours=9)
        )
        db.add(san8)
        await db.flush()

        rel8 = ReleaseAuthorization(
            return_item_id=item8.id,
            authorized_disposition=AuthorizedDisposition.RESALE_SECONDARY_MARKET,
            resale_proceeds_actual=Decimal("620.00"),
            verified_sanitization_id=san8.id,
            authorized_by_user_id=user_admin.id,
            released_at=now_utc - timedelta(hours=8)
        )
        refund8 = RefundRecord(
            return_request_id=req8.id,
            refund_amount=Decimal("799.00"),
            status=RefundStatus.COMPLETED,
            initiated_at=now_utc - timedelta(days=2),
            completed_at=now_utc - timedelta(days=1),
            external_payout_ref="TXN-ACH-20261028-9901",
            manual_processing_notes="Full payment reimbursed via ACH direct deposit."
        )
        db.add_all([rel8, refund8])

        # -------------------------------------------------------------------
        # CASE 9: COMPLETED (5-Day SLA Timeout Auto-Returned to Nova)
        # -------------------------------------------------------------------
        req9 = ReturnRequest(
            case_number="RET-20261030-1009",
            external_order_ref="ORD-NOV-4455-66",
            customer_name="John Shepard",
            customer_email="jshepard@example.com",
            customer_phone="555-0911",
            pickup_address="2148 Normandy Drive",
            pickup_city="San Francisco",
            pickup_postal_code="94115",
            status=ReturnCaseStatus.COMPLETED,
            created_by_user_id=user_admin.id
        )
        db.add(req9)
        await db.flush()

        item9 = ReturnItem(
            return_request_id=req9.id,
            manufacturer_org_id=org_nova.id,
            item_tag="TAG-NOVA-3322",
            product_name="Nova Gaming Display 27Q",
            product_category=ProductCategory.MONITOR,
            model_number="NGD-27-QHD",
            declared_serial_number="SN-NOV-332299",
            verified_serial_number="SN-NOV-332299",
            return_reason="Dead pixel cluster near display center",
            recovery_classification=RecoveryClassification.RETURN_TO_MANUFACTURER,
            approval_status=ApprovalStatus.APPROVED,
            current_custody_location=CustodyLocation.DELIVERED_TO_MANUFACTURER,
            requires_data_sanitization=False
        )
        db.add(item9)
        await db.flush()

        refund9 = RefundRecord(
            return_request_id=req9.id,
            refund_amount=Decimal("450.00"),
            status=RefundStatus.COMPLETED,
            initiated_at=now_utc - timedelta(days=6),
            completed_at=now_utc - timedelta(days=5),
            external_payout_ref="TXN-ACH-20261025-1104",
            manual_processing_notes="Automated refund closed after SLA dispatch."
        )
        custody_evt9 = CustodyEvent(
            return_item_id=item9.id,
            actor_user_id=user_admin.id,
            event_type=CustodyEventType.DISPATCH_TO_MANUFACTURER,
            from_location="WAREHOUSE",
            to_location="DELIVERED_TO_MANUFACTURER",
            carrier_tracking_ref="FEDEX-778899221144",
            notes="Dispatched to Nova Computing Systems per contractual 5-Day SLA auto-return."
        )
        db.add_all([refund9, custody_evt9])

        # -------------------------------------------------------------------
        # Audit Logs for Traceability
        # -------------------------------------------------------------------
        audit1 = AuditEvent(
            actor_user_id=user_admin.id,
            action="CREATE_RETURN_REQUEST",
            entity_name="ReturnRequest",
            entity_id=req1.id,
            new_state={"case_number": "RET-20261030-1001", "status": "RETURN_REQUESTED"},
            reason="Customer initiated intake request via support desk."
        )
        audit2 = AuditEvent(
            actor_user_id=user_agent.id,
            action="FIELD_VERIFICATION",
            entity_name="ReturnItem",
            entity_id=item2.id,
            new_state={"verification_outcome": "VERIFIED", "damage": "LOW"},
            reason="Agent verified serial number and exterior cosmetic grade."
        )
        audit3 = AuditEvent(
            actor_user_id=user_ops.id,
            action="WAREHOUSE_INTAKE_SCAN",
            entity_name="ReturnItem",
            entity_id=item3.id,
            new_state={"custody": "WAREHOUSE", "bin": "BIN-A1-04"},
            reason="Dock receipt confirmed at Central Depot."
        )
        audit4 = AuditEvent(
            actor_user_id=user_tech.id,
            action="DATA_SANITIZATION_PASSED",
            entity_name="ReturnItem",
            entity_id=item8.id,
            new_state={"sanitization_status": "PASSED", "cert": "CERT-NIST-APX-7744-PURGE"},
            reason="NIST SP 800-88 Purge verified cryptographically."
        )
        audit5 = AuditEvent(
            actor_user_id=user_admin.id,
            action="RELEASE_FOR_RESALE",
            entity_name="ReturnItem",
            entity_id=item8.id,
            new_state={"custody": "WAREHOUSE", "disposition": "RESALE_SECONDARY_MARKET"},
            reason="Resale release authorized with verified NIST sanitization certificate."
        )
        db.add_all([audit1, audit2, audit3, audit4, audit5])

        await db.commit()

        print("Database seeded successfully with 9 multi-stage demo return cases!")
        print("\nDemo Credentials (password for all is 'password123'):")
        print("  Admin:           admin@reverse-logistics.com")
        print("  Agent:           agent@reverse-logistics.com")
        print("  Ops Spec:        ops@reverse-logistics.com")
        print("  Approver (Apex): approver@apex.com")
        print("  Approver (Nova): approver@nova.com")
        print("  Analyst:         analyst@reverse-logistics.com")
        print("  Technician:      tech@reverse-logistics.com")


if __name__ == "__main__":
    asyncio.run(seed())
