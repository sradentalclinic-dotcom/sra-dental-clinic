from datetime import date, datetime
from typing import Optional
import xml.etree.ElementTree as ET
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# Database Configuration
DATABASE_URL = "sqlite:///./aura_dental.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Models ---
class ProcedureModel(Base):
    __tablename__ = "procedures"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    price = Column(Float, nullable=False)

class PatientModel(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, unique=True, index=True)
    patient_name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    phone_number = Column(String, nullable=False)
    patient_place = Column(String, nullable=True)
    procedure_id = Column(Integer, ForeignKey("procedures.id"))
    units = Column(Integer, default=1)
    payment_done = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    next_appointment = Column(Date, nullable=True)
    next_appointment_time = Column(String, nullable=True)
    operatory_chair = Column(String, default="Operatory 1")
    created_date = Column(Date, default=date.today)

    procedure = relationship("ProcedureModel")

class LabOrderModel(Base):
    __tablename__ = "lab_orders"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, index=True)
    lab_item = Column(String, nullable=False)
    units = Column(Integer, default=1)
    lab_name = Column(String, default="Premier Dental Lab")
    total_lab_cost = Column(Float, nullable=False)
    status = Column(String, default="Pending")
    payment_status = Column(String, default="Unpaid")
    order_date = Column(Date, default=date.today)

class ArchSummaryModel(Base):
    __tablename__ = "arch_summaries"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, index=True)
    maxillary_status = Column(String)
    maxillary_notes = Column(String)
    mandibular_status = Column(String)
    mandibular_teeth_count = Column(Integer)

class ExtractionModel(Base):
    __tablename__ = "extractions"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, index=True)
    tooth_universal = Column(String)
    fdi = Column(String)
    tooth_name = Column(String)
    procedure_code = Column(String)
    description = Column(String)
    anesthesia = Column(String)
    complications = Column(String)
    status = Column(String)

class EndoRecordModel(Base):
    __tablename__ = "endo_records"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, index=True)
    tooth_universal = Column(String)
    fdi = Column(String)
    tooth_name = Column(String)
    procedure_code = Column(String)
    description = Column(String)
    system_used = Column(String)
    irrigants = Column(String)
    master_apical_file = Column(String)
    obturation = Column(String)
    status = Column(String)
    canals = relationship("CanalModel", back_populates="endo", cascade="all, delete-orphan")

class CanalModel(Base):
    __tablename__ = "canals"
    id = Column(Integer, primary_key=True, index=True)
    endo_record_id = Column(Integer, ForeignKey("endo_records.id"))
    canal_name = Column(String)
    reference_point = Column(String)
    working_length = Column(String)
    master_file = Column(String)
    status = Column(String)
    endo = relationship("EndoRecordModel", back_populates="canals")

class AttachmentModel(Base):
    __tablename__ = "diagnostic_attachments"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, index=True)
    attachment_id = Column(String)
    type = Column(String)
    label = Column(String)
    mime_type = Column(String)
    secure_url = Column(String)
    status = Column(String)

Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class PatientCreate(BaseModel):
    patient_name: str
    age: Optional[int] = None
    phone_number: str
    patient_place: Optional[str] = "Mandi Dabwali"
    procedure_id: int
    units: int = 1
    payment_done: float = 0.0
    discount: float = 0.0
    next_appointment: Optional[str] = None
    next_appointment_time: Optional[str] = None
    operatory_chair: str = "Operatory 1"

class PatientUpdate(BaseModel):
    patient_name: str
    age: Optional[int] = None
    phone_number: str
    patient_place: Optional[str] = None
    units: int
    payment_done: float
    discount: float

class LabOrderCreate(BaseModel):
    opd_number: str
    lab_item: str
    units: int = 1
    lab_name: str = "Premier Dental Lab"

class XMLImportPayload(BaseModel):
    xml_data: str

# --- FastAPI App Initialization ---
app = FastAPI(title="AURA Dental Clinical Suite API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def seed_procedures():
    db = SessionLocal()
    if db.query(ProcedureModel).count() == 0:
        default_procedures = [
            ("Consultation / Examination", 200),
            ("Digital X-Ray (RVG)", 150),
            ("Ultrasonic Scaling & Polishing", 800),
            ("Composite Restoration (Filling)", 1000),
            ("Glass Ionomer Cement (GIC) Filling", 600),
            ("Root Canal Treatment (Single Root)", 2500),
            ("Root Canal Treatment (Multi Root)", 3500),
            ("Post & Core Buildup", 1500),
            ("Simple Tooth Extraction", 500),
            ("Surgical Tooth Extraction / Impaction", 2500),
            ("PFM Crown (Per Unit)", 1500),
            ("Zirconia Crown (Per Unit)", 3500),
            ("Complete Denture (Full Arch)", 10000),
            ("Removable Partial Denture (RPD)", 2000),
            ("Dental Implant Placement", 18000),
            ("Teeth Whitening (Bleaching)", 4000),
            ("Orthodontic Braces (Per Arch)", 15000),
            ("Clear Aligners (Full Course)", 50000),
            ("Periodontal Flap Surgery", 4000),
            ("Gingivectomy (Per Quadrant)", 2000),
            ("Fluoride Treatment", 800),
            ("Pit and Fissure Sealant", 500),
            ("Emergency Pain Management", 500)
        ]
        for name, price in default_procedures:
            db.add(ProcedureModel(name=name, price=price))
        db.commit()
    db.close()

# --- API Endpoints ---

@app.get("/procedures")
def get_procedures(db: Session = Depends(get_db)):
    procedures = db.query(ProcedureModel).all()
    return [{"id": p.id, "name": p.name, "price": p.price} for p in procedures]

@app.post("/patients")
def register_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    count = db.query(PatientModel).count()
    opd_number = f"OPD-{101 + count}"

    next_appt_date = None
    if payload.next_appointment:
        try:
            next_appt_date = datetime.strptime(payload.next_appointment, "%Y-%m-%d").date()
        except ValueError:
            pass

    patient = PatientModel(
        opd_number=opd_number,
        patient_name=payload.patient_name,
        age=payload.age,
        phone_number=payload.phone_number,
        patient_place=payload.patient_place,
        procedure_id=payload.procedure_id,
        units=payload.units,
        payment_done=payload.payment_done,
        discount=payload.discount,
        next_appointment=next_appt_date,
        next_appointment_time=payload.next_appointment_time,
        operatory_chair=payload.operatory_chair,
        created_date=date.today()
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {"status": "success", "opd_number": opd_number, "patient_id": patient.id}

@app.post("/patients/import-xml")
def import_patient_xml(payload: XMLImportPayload, db: Session = Depends(get_db)):
    try:
        root = ET.fromstring(payload.xml_data)
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML format: {str(e)}")

    header = root.find("PatientHeader")
    patient_id = header.find("PatientID").text if header is not None and header.find("PatientID") is not None else "PT-904281"
    operatory = header.find("OperatoryRoom").text if header is not None and header.find("OperatoryRoom") is not None else "Op-03"

    opd_number = f"OPD-{patient_id.replace('PT-', '')}"
    existing = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if not existing:
        patient = PatientModel(
            opd_number=opd_number,
            patient_name=f"Patient {patient_id}",
            age=42,
            phone_number="9876543210",
            patient_place="Mandi Dabwali",
            procedure_id=6,
            units=1,
            payment_done=2500.0,
            discount=0.0,
            operatory_chair=operatory,
            created_date=date.today()
        )
        db.add(patient)
        db.commit()

    # Parse Arch Summary
    arch_summary = root.find("ArchSummary")
    if arch_summary is not None:
        max_status, max_notes, mand_status, mand_count = "", "", "", 0
        for arch in arch_summary.findall("Arch"):
            region = arch.attrib.get("region")
            if region == "Maxillary_Upper":
                max_status = arch.attrib.get("status")
                max_notes = arch.findtext("Notes")
            elif region == "Mandibular_Lower":
                mand_status = arch.attrib.get("status")
                mand_count = int(arch.findtext("ActiveTeethCount") or 0)
        
        # Upsert Arch Summary
        existing_arch = db.query(ArchSummaryModel).filter(ArchSummaryModel.opd_number == opd_number).first()
        if existing_arch:
            existing_arch.maxillary_status = max_status
            existing_arch.maxillary_notes = max_notes
            existing_arch.mandibular_status = mand_status
            existing_arch.mandibular_teeth_count = mand_count
        else:
            arch_rec = ArchSummaryModel(
                opd_number=opd_number,
                maxillary_status=max_status,
                maxillary_notes=max_notes,
                mandibular_status=mand_status,
                mandibular_teeth_count=mand_count
            )
            db.add(arch_rec)

    # Parse Extractions
    extractions = root.find("Extractions")
    if extractions is not None:
        for proc in extractions.findall("ProcedureRecord"):
            tooth = proc.find("ToothNumber")
            ext = ExtractionModel(
                opd_number=opd_number,
                tooth_universal=tooth.attrib.get("Universal") if tooth is not None else "",
                fdi=tooth.attrib.get("FDI") if tooth is not None else "",
                tooth_name=tooth.text if tooth is not None else "",
                procedure_code=proc.findtext("ProcedureCode"),
                description=proc.findtext("Description"),
                anesthesia=proc.findtext("Anesthesia"),
                complications=proc.findtext("Complications"),
                status=proc.findtext("Status")
            )
            db.add(ext)

    # Parse Endodontics
    endos = root.find("Endodontics")
    if endos is not None:
        for proc in endos.findall("ProcedureRecord"):
            tooth = proc.find("ToothNumber")
            endo = EndoRecordModel(
                opd_number=opd_number,
                tooth_universal=tooth.attrib.get("Universal") if tooth is not None else "",
                fdi=tooth.attrib.get("FDI") if tooth is not None else "",
                tooth_name=tooth.text if tooth is not None else "",
                procedure_code=proc.findtext("ProcedureCode"),
                description=proc.findtext("Description"),
                system_used=proc.findtext("SystemUsed"),
                irrigants=proc.findtext("Irrigants"),
                master_apical_file=proc.findtext("MasterApicalFile"),
                obturation=proc.findtext("Obturation"),
                status=proc.findtext("Status")
            )
            db.add(endo)
            db.flush()

            canal_chart = proc.find("CanalChart")
            if canal_chart is not None:
                for c in canal_chart.findall("Canal"):
                    canal = CanalModel(
                        endo_record_id=endo.id,
                        canal_name=c.attrib.get("name"),
                        reference_point=c.findtext("ReferencePoint"),
                        working_length=c.findtext("WorkingLength"),
                        master_file=c.findtext("MasterFile"),
                        status=c.findtext("Status")
                    )
                    db.add(canal)

    # Parse Diagnostic Attachments
    attachments = root.find("DiagnosticAttachments")
    if attachments is not None:
        for att in attachments.findall("Attachment"):
            attachment = AttachmentModel(
                opd_number=opd_number,
                attachment_id=att.attrib.get("id"),
                type=att.attrib.get("type"),
                label=att.findtext("Label"),
                mime_type=att.findtext("MimeType"),
                secure_url=att.findtext("SecureAccessURL"),
                status=att.findtext("Status")
            )
            db.add(attachment)

    db.commit()
    return {"status": "success", "opd_number": opd_number, "message": "Clinical XML and Arch Summary Imported Successfully"}

@app.get("/patients/{opd_number}")
def get_patient(opd_number: str, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    proc = db.query(ProcedureModel).filter(ProcedureModel.id == patient.procedure_id).first()
    return {
        "opd_number": patient.opd_number,
        "patient_name": patient.patient_name,
        "age": patient.age,
        "phone_number": patient.phone_number,
        "patient_place": patient.patient_place,
        "procedure_name": proc.name if proc else "Unknown",
        "base_price": proc.price if proc else 0,
        "units": patient.units,
        "total_paid": patient.payment_done,
        "discount": patient.discount,
        "next_appointment": str(patient.next_appointment) if patient.next_appointment else "",
        "next_appointment_time": patient.next_appointment_time or "",
        "operatory_chair": patient.operatory_chair
    }

@app.get("/patients/{opd_number}/clinical-records")
def get_clinical_records(opd_number: str, db: Session = Depends(get_db)):
    arch_summary = db.query(ArchSummaryModel).filter(ArchSummaryModel.opd_number == opd_number).first()
    extractions = db.query(ExtractionModel).filter(ExtractionModel.opd_number == opd_number).all()
    endos = db.query(EndoRecordModel).filter(EndoRecordModel.opd_number == opd_number).all()
    attachments = db.query(AttachmentModel).filter(AttachmentModel.opd_number == opd_number).all()

    arch_data = None
    if arch_summary:
        arch_data = {
            "maxillary_status": arch_summary.maxillary_status,
            "maxillary_notes": arch_summary.maxillary_notes,
            "mandibular_status": arch_summary.mandibular_status,
            "mandibular_teeth_count": arch_summary.mandibular_teeth_count
        }

    endo_list = []
    for e in endos:
        canals = [{
            "name": c.canal_name,
            "ref_point": c.reference_point,
            "wl": c.working_length,
            "master_file": c.master_file,
            "status": c.status
        } for c in e.canals]
        endo_list.append({
            "tooth_universal": e.tooth_universal,
            "fdi": e.fdi,
            "tooth_name": e.tooth_name,
            "procedure_code": e.procedure_code,
            "description": e.description,
            "system_used": e.system_used,
            "irrigants": e.irrigants,
            "master_apical_file": e.master_apical_file,
            "obturation": e.obturation,
            "status": e.status,
            "canals": canals
        })

    ext_list = [{
        "tooth_universal": x.tooth_universal,
        "fdi": x.fdi,
        "tooth_name": x.tooth_name,
        "procedure_code": x.procedure_code,
        "description": x.description,
        "anesthesia": x.anesthesia,
        "complications": x.complications,
        "status": x.status
    } for x in extractions]

    att_list = [{
        "id": a.attachment_id,
        "type": a.type,
        "label": a.label,
        "mime_type": a.mime_type,
        "url": a.secure_url,
        "status": a.status
    } for a in attachments]

    return {
        "arch_summary": arch_data,
        "extractions": ext_list,
        "endodontics": endo_list,
        "attachments": att_list
    }

@app.put("/patients/{opd_number}")
def update_patient(opd_number: str, payload: PatientUpdate, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.patient_name = payload.patient_name
    patient.age = payload.age
    patient.phone_number = payload.phone_number
    if payload.patient_place:
        patient.patient_place = payload.patient_place
    patient.units = payload.units
    patient.payment_done = payload.payment_done
    patient.discount = payload.discount
    db.commit()
    return {"status": "updated"}

@app.delete("/patients/{opd_number}")
def delete_patient(opd_number: str, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
    return {"status": "deleted"}

@app.post("/lab-orders")
def create_lab_order(payload: LabOrderCreate, db: Session = Depends(get_db)):
    LAB_RATES = {"PFM": 350, "Zirconia": 900, "Denture": 1100, "Metal Cap": 150, "RPD": 50}
    unit_cost = LAB_RATES.get(payload.lab_item, 350)
    total_cost = unit_cost * payload.units

    order = LabOrderModel(
        opd_number=payload.opd_number,
        lab_item=payload.lab_item,
        units=payload.units,
        lab_name=payload.lab_name,
        total_lab_cost=total_cost,
        status="In Lab",
        payment_status="Unpaid",
        order_date=date.today()
    )
    db.add(order)
    db.commit()
    return {"status": "created", "total_lab_cost": total_cost}

@app.get("/lab-orders")
def get_lab_orders(db: Session = Depends(get_db)):
    orders = db.query(LabOrderModel).all()
    results = []
    for o in orders:
        patient = db.query(PatientModel).filter(PatientModel.opd_number == o.opd_number).first()
        results.append({
            "id": o.id,
            "date": str(o.order_date),
            "opd_number": o.opd_number,
            "patient_name": patient.patient_name if patient else "Unknown",
            "lab_item": o.lab_item,
            "units": o.units,
            "total_lab_cost": o.total_lab_cost,
            "status": o.status,
            "payment_status": o.payment_status
        })
    return results

@app.delete("/lab-orders/{order_id}")
def delete_lab_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(LabOrderModel).filter(LabOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"status": "deleted"}

@app.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    today = date.today()
    patients = db.query(PatientModel).all()
    lab_orders = db.query(LabOrderModel).all()

    today_revenue = sum(p.payment_done for p in patients if p.created_date == today)
    month_revenue = sum(p.payment_done for p in patients if p.created_date and p.created_date.month == today.month and p.created_date.year == today.year)
    
    total_dues = 0
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        if proc:
            total_bill = max(0, (proc.price * p.units) - p.discount)
            due = total_bill - p.payment_done
            if due > 0:
                total_dues += due

    total_lab_dues = sum(l.total_lab_cost for l in lab_orders if l.payment_status == "Unpaid")
    today_opd = sum(1 for p in patients if p.created_date == today)
    total_opd = len(patients)

    return {
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "total_dues": total_dues,
        "total_lab_dues": total_lab_dues,
        "today_opd": today_opd,
        "total_opd": total_opd
    }

@app.get("/views/appointments")
def get_appointments(db: Session = Depends(get_db)):
    today = date.today()
    patients = db.query(PatientModel).filter(PatientModel.next_appointment == today).all()
    today_list = []
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        total_bill = max(0, (proc.price * p.units) - p.discount) if proc else 0
        pending = max(0, total_bill - p.payment_done)
        today_list.append({
            "opd_number": p.opd_number,
            "patient_name": p.patient_name,
            "phone": p.phone_number,
            "procedure": proc.name if proc else "General",
            "units": p.units,
            "operatory_chair": p.operatory_chair,
            "time_slot": p.next_appointment_time or "11:00",
            "pending_payment": pending
        })
    return {"today": today_list}

@app.get("/views/daily-log")
def get_daily_log(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(PatientModel)
    if search:
        query = query.filter((PatientModel.patient_name.ilike(f"%{search}%")) | (PatientModel.opd_number.ilike(f"%{search}%")))
    
    patients = query.all()
    results = []
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        total_bill = max(0, (proc.price * p.units) - p.discount) if proc else 0
        pending = max(0, total_bill - p.payment_done)
        results.append({
            "date": str(p.created_date),
            "opd_number": p.opd_number,
            "patient_name": p.patient_name,
            "procedure": proc.name if proc else "General",
            "units": p.units,
            "total_amount": total_bill,
            "total_paid": p.payment_done,
            "payment_left": pending,
            "phone": p.phone_number
        })
    return results
