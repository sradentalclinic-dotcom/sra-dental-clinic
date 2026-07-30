from datetime import date, datetime, timedelta
from typing import Optional
import os
import json
from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import Column, Date, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database Setup
DATABASE_URL = "sqlite:///./sra_dental.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

os.makedirs("uploads", exist_ok=True)

class ProcedureModel(Base):
    __tablename__ = "procedures"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    price = Column(Float)
    gap_days = Column(Integer, default=0)
    total_sittings = Column(Integer, default=1)

class PatientModel(Base):
    __tablename__ = "patients"
    opd_number = Column(String, primary_key=True, index=True)
    patient_name = Column(String)
    phone_number = Column(String)
    patient_place = Column(String, default="Mandi Dabwali")
    procedure_id = Column(Integer)
    total_sittings = Column(Integer, default=1)
    current_sitting = Column(Integer, default=1)
    base_price = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    total_amount = Column(Float)
    total_paid = Column(Float, default=0.0)
    payment_left = Column(Float)
    time_slot = Column(String)
    next_appointment = Column(Date, nullable=True)
    created_date = Column(Date, default=date.today)
    source = Column(String, default="Website")
    xray_path = Column(String, nullable=True)
    extracted_tooth = Column(String, nullable=True)
    operatory_chair = Column(String, default="Operatory 1")
    medical_alerts = Column(Text, nullable=True)

class EndoChartModel(Base):
    __tablename__ = "endo_charts"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, index=True)
    tooth_number = Column(String)
    canals_data = Column(Text)  # Stores JSON array of hand-typed canal entries

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SRA Dental Enterprise Operatory Suite")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def serve_patient_portal():
    return FileResponse("patient.html")

@app.get("/admin")
def serve_admin_portal():
    return FileResponse("index.html")

@app.get("/procedures")
def get_procedures(db: Session = Depends(get_db)):
    procs = db.query(ProcedureModel).all()
    if not procs:
        defaults = [
            ProcedureModel(name="RCT ANTERIOR", price=2000, gap_days=3, total_sittings=3),
            ProcedureModel(name="RCT POSTERIOR", price=2500, gap_days=3, total_sittings=3),
            ProcedureModel(name="RCT PEDO", price=2000, gap_days=3, total_sittings=3),
            ProcedureModel(name="CONSULTATION", price=100, gap_days=0, total_sittings=1),
            ProcedureModel(name="TEMPORARY FILLING", price=100, gap_days=0, total_sittings=1),
            ProcedureModel(name="EXTRACTION", price=500, gap_days=2, total_sittings=2),
            ProcedureModel(name="SURGICAL EXTRACTION", price=3000, gap_days=7, total_sittings=2),
            ProcedureModel(name="SCALING", price=1000, gap_days=0, total_sittings=1),
            ProcedureModel(name="PFM CROWN", price=2000, gap_days=3, total_sittings=2),
            ProcedureModel(name="ZIRCONIA CROWN", price=4000, gap_days=3, total_sittings=2)
        ]
        db.add_all(defaults)
        db.commit()
        procs = db.query(ProcedureModel).all()
    return [{"id": p.id, "name": p.name, "price": p.price, "gap_days": p.gap_days, "total_sittings": p.total_sittings} for p in procs]

@app.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    today = date.today()
    patients = db.query(PatientModel).all()
    today_revenue = sum(p.total_paid for p in patients if p.created_date == today)
    month_revenue = sum(p.total_paid for p in patients if p.created_date and p.created_date.month == today.month and p.created_date.year == today.year)
    total_dues = sum(p.payment_left for p in patients)
    today_opd = sum(1 for p in patients if p.created_date == today)
    total_opd = len(patients)
    
    return {
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "total_dues": total_dues,
        "today_opd": today_opd,
        "total_opd": total_opd,
        "reel_leads": sum(1 for p in patients if p.source == "Instagram Reel"),
        "web_leads": sum(1 for p in patients if p.source == "Website")
    }

class PatientCreate(BaseModel):
    patient_name: str
    phone_number: str
    patient_place: Optional[str] = "Mandi Dabwali"
    procedure_id: int
    time_slot: str
    payment_done: float
    discount: float = 0.0
    next_appointment: Optional[str] = None
    source: str = "Website"
    extracted_tooth: Optional[str] = None
    operatory_chair: Optional[str] = "Operatory 1"
    medical_alerts: Optional[str] = None

@app.post("/patients")
def create_patient(data: PatientCreate, db: Session = Depends(get_db)):
    count = db.query(PatientModel).count() + 1
    opd_number = f"OPD-{100 + count}"
    proc = db.query(ProcedureModel).filter(ProcedureModel.id == data.procedure_id).first()
    base_amt = proc.price if proc else 0.0
    total_amt = max(0.0, base_amt - data.discount)
    payment_left = max(0.0, total_amt - data.payment_done)
    next_date = datetime.strptime(data.next_appointment, "%Y-%m-%d").date() if data.next_appointment else None

    new_patient = PatientModel(
        opd_number=opd_number,
        patient_name=data.patient_name,
        phone_number=data.phone_number,
        patient_place=data.patient_place,
        procedure_id=data.procedure_id,
        total_sittings=proc.total_sittings if proc else 1,
        base_price=base_amt,
        discount=data.discount,
        total_amount=total_amt,
        total_paid=data.payment_done,
        payment_left=payment_left,
        time_slot=data.time_slot,
        next_appointment=next_date,
        source=data.source,
        extracted_tooth=data.extracted_tooth,
        operatory_chair=data.operatory_chair,
        medical_alerts=data.medical_alerts
    )
    db.add(new_patient)
    db.commit()
    return {"message": "Patient registered successfully", "opd_number": opd_number}

@app.get("/patients/{opd_number}")
def get_patient_details(opd_number: str, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")
    proc = db.query(ProcedureModel).filter(ProcedureModel.id == patient.procedure_id).first()
    
    charts = db.query(EndoChartModel).filter(EndoChartModel.opd_number == opd_number).all()
    saved_charts = {c.tooth_number: json.loads(c.canals_data) for c in charts}

    return {
        "opd_number": patient.opd_number,
        "patient_name": patient.patient_name,
        "phone_number": patient.phone_number,
        "patient_place": patient.patient_place,
        "procedure_name": proc.name if proc else "General",
        "total_amount": patient.total_amount,
        "total_paid": patient.total_paid,
        "payment_left": patient.payment_left,
        "source": patient.source,
        "operatory_chair": patient.operatory_chair,
        "medical_alerts": patient.medical_alerts,
        "charts": saved_charts
    }

@app.post("/patients/{opd_number}/upload-treatment-file")
async def upload_treatment_file(
    opd_number: str, 
    file_type: str = Form(...), 
    tooth_number: str = Form(...), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    file_path = f"uploads/{opd_number}_Tooth_{tooth_number}_{file_type}_{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    patient = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if patient and file_type == "XRAY":
        patient.xray_path = f"/{file_path}"
        db.commit()

    return {"message": f"{file_type} File Uploaded successfully", "path": f"/{file_path}"}

class EndoSaveRequest(BaseModel):
    opd_number: str
    tooth_number: str
    canals_data: str  # JSON formatted hand-typed entries

@app.post("/patients/endo-chart")
def save_endo_chart(data: EndoSaveRequest, db: Session = Depends(get_db)):
    chart = db.query(EndoChartModel).filter(
        EndoChartModel.opd_number == data.opd_number, 
        EndoChartModel.tooth_number == data.tooth_number
    ).first()
    
    if chart:
        chart.canals_data = data.canals_data
    else:
        chart = EndoChartModel(opd_number=data.opd_number, tooth_number=data.tooth_number, canals_data=data.canals_data)
        db.add(chart)
    db.commit()
    return {"message": "Endo chart saved successfully"}

@app.get("/views/appointments")
def get_appointments(db: Session = Depends(get_db)):
    today = date.today()
    patients = db.query(PatientModel).all()
    today_list = []
    future_list = []
    
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        item = {
            "opd_number": p.opd_number,
            "patient_name": p.patient_name,
            "phone": p.phone_number,
            "patient_place": p.patient_place,
            "procedure": proc.name if proc else "General",
            "time_slot": p.time_slot,
            "pending_payment": p.payment_left,
            "operatory_chair": p.operatory_chair,
            "next_appointment": p.next_appointment.isoformat() if p.next_appointment else None
        }
        if p.next_appointment == today:
            today_list.append(item)
        elif p.next_appointment and p.next_appointment > today:
            future_list.append(item)
            
    return {"today": today_list, "future": future_list}

@app.get("/views/daily-log")
def daily_log(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(PatientModel)
    if search:
        query = query.filter((PatientModel.patient_name.contains(search)) | (PatientModel.opd_number.contains(search)))
    patients = query.all()
    logs = []
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        logs.append({
            "opd_number": p.opd_number,
            "date": p.created_date.isoformat(),
            "patient_name": p.patient_name,
            "patient_place": p.patient_place,
            "procedure": proc.name if proc else "General",
            "current_sitting": p.current_sitting,
            "total_sittings": p.total_sittings,
            "total_amount": p.total_amount,
            "total_paid": p.total_paid,
            "payment_left": p.payment_left,
            "source": p.source,
            "chair": p.operatory_chair
        })
    return list(reversed(logs))
