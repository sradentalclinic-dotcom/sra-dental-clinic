from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import Column, Date, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database Setup
DATABASE_URL = "sqlite:///./sra_dental.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class ProcedureModel(Base):
    __tablename__ = "procedures"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    price = Column(Float)
    gap_days = Column(Integer, default=0)

class PatientModel(Base):
    __tablename__ = "patients"
    opd_number = Column(String, primary_key=True, index=True)
    patient_name = Column(String)
    phone_number = Column(String)
    procedure_id = Column(Integer)
    total_sittings = Column(Integer, default=1)
    current_sitting = Column(Integer, default=1)
    total_amount = Column(Float)
    total_paid = Column(Float, default=0.0)
    payment_left = Column(Float)
    time_slot = Column(String)
    next_appointment = Column(Date, nullable=True)
    created_date = Column(Date, default=date.today)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SRA Dental Clinic API")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- WEB PAGE ROUTES (Serves your website files directly) ---
@app.get("/")
def serve_patient_portal():
    return FileResponse("patient.html")

@app.get("/admin")
def serve_admin_portal():
    return FileResponse("index.html")

# --- API ENDPOINTS ---
@app.get("/procedures")
def get_procedures(db: Session = Depends(get_db)):
    procs = db.query(ProcedureModel).all()
    if not procs:
        # Seed default procedures if empty
        defaults = [
            ProcedureModel(name="Consultation", price=300, gap_days=0),
            ProcedureModel(name="Root Canal Treatment", price=3500, gap_days=3),
            ProcedureModel(name="Dental Implants", price=15000, gap_days=7),
            ProcedureModel(name="Scaling & Polishing", price=1000, gap_days=0),
            ProcedureModel(name="Tooth Extraction", price=800, gap_days=0)
        ]
        db.add_all(defaults)
        db.commit()
        procs = db.query(ProcedureModel).all()
    return procs

@app.get("/calculate-next-date")
def calculate_next_date(gap_days: int = Query(...)):
    next_date = date.today() + timedelta(days=gap_days)
    return {"next_date": next_date.isoformat()}

@app.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    today = date.today()
    patients = db.query(PatientModel).all()
    
    today_revenue = sum(p.total_paid for p in patients if p.created_date == today)
    month_revenue = sum(p.total_paid for p in patients if p.created_date.month == today.month and p.created_date.year == today.year)
    total_dues = sum(p.payment_left for p in patients)
    
    return {
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "total_dues": total_dues
    }

@app.get("/views/appointments")
def get_appointments(db: Session = Depends(get_db)):
    today = date.today()
    patients = db.query(PatientModel).all()
    
    today_list = []
    future_list = []
    
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        proc_name = proc.name if proc else "General"
        
        wa_text = f"Hello {p.patient_name}, this is a reminder for your dental appointment at SRA Dental Clinic today at {p.time_slot}."
        wa_link = f"https://wa.me/91{p.phone_number}?text={wa_text.replace(' ', '%20')}" if p.phone_number else ""
        
        item = {
            "opd_number": p.opd_number,
            "patient_name": p.patient_name,
            "phone": p.phone_number,
            "procedure": proc_name,
            "time_slot": p.time_slot,
            "pending_payment": p.payment_left,
            "whatsapp_link": wa_link,
            "next_appointment": p.next_appointment.isoformat() if p.next_appointment else None
        }
        
        if p.next_appointment == today:
            today_list.append(item)
        elif p.next_appointment and p.next_appointment > today:
            future_list.append(item)
            
    return {"today": today_list, "future": future_list}

class PatientCreate(BaseModel):
    patient_name: str
    phone_number: str
    procedure_id: int
    time_slot: str
    payment_done: float
    next_appointment: Optional[str] = None

@app.post("/patients")
def create_patient(data: PatientCreate, db: Session = Depends(get_db)):
    count = db.query(PatientModel).count() + 1
    opd_number = f"OPD-{100 + count}"
    
    proc = db.query(ProcedureModel).filter(ProcedureModel.id == data.procedure_id).first()
    total_amt = proc.price if proc else 0.0
    payment_left = max(0.0, total_amt - data.payment_done)
    
    next_date = datetime.strptime(data.next_appointment, "%Y-%m-%d").date() if data.next_appointment else None
    
    new_patient = PatientModel(
        opd_number=opd_number,
        patient_name=data.patient_name,
        phone_number=data.phone_number,
        procedure_id=data.procedure_id,
        total_amount=total_amt,
        total_paid=data.payment_done,
        payment_left=payment_left,
        time_slot=data.time_slot,
        next_appointment=next_date
    )
    db.add(new_patient)
    db.commit()
    return {"message": "Success", "opd_number": opd_number}

class FollowUpCreate(BaseModel):
    opd_number: str
    payment_done: float
    time_slot: str
    next_appointment: Optional[str] = None

@app.post("/patients/follow-up")
def follow_up(data: FollowUpCreate, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == data.opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, model_detail="Patient not found")
        
    patient.current_sitting += 1
    patient.total_paid += data.payment_done
    patient.payment_left = max(0.0, patient.total_amount - patient.total_paid)
    patient.time_slot = data.time_slot
    patient.next_appointment = datetime.strptime(data.next_appointment, "%Y-%m-%d").date() if data.next_appointment else None
    
    db.commit()
    return {"message": "Follow-up logged"}

@app.get("/views/daily-log")
def daily_log(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(PatientModel)
    if search:
        query = query.filter(
            (PatientModel.patient_name.contains(search)) |
            (PatientModel.phone_number.contains(search)) |
            (PatientModel.opd_number.contains(search))
        )
    patients = query.all()
    logs = []
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        logs.append({
            "opd_number": p.opd_number,
            "date": p.created_date.isoformat(),
            "patient_name": p.patient_name,
            "procedure": proc.name if proc else "General",
            "current_sitting": p.current_sitting,
            "total_sittings": p.total_sittings,
            "payment_done": p.total_paid, # simplified for log view
            "total_paid": p.total_paid,
            "payment_left": p.payment_left,
            "next_appointment": p.next_appointment.isoformat() if p.next_appointment else None
        })
    return logs