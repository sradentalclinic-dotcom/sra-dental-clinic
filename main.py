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
    patient_place = Column(String, default="")
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
    source = Column(String, default="Walkin")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SRA Dental Clinic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            ProcedureModel(name="GIC FILLING", price=500, gap_days=0, total_sittings=1),
            ProcedureModel(name="COMPOSITE FILLING", price=1000, gap_days=0, total_sittings=1),
            ProcedureModel(name="EXTRACTION", price=500, gap_days=2, total_sittings=2),
            ProcedureModel(name="SURGICAL EXTRACTION", price=3000, gap_days=7, total_sittings=2),
            ProcedureModel(name="SCALING", price=1000, gap_days=0, total_sittings=1),
            ProcedureModel(name="METAL CROWN", price=1500, gap_days=3, total_sittings=2),
            ProcedureModel(name="PFM CROWN", price=2000, gap_days=3, total_sittings=2),
            ProcedureModel(name="PREMIUM PFM CROWN", price=2500, gap_days=3, total_sittings=2),
            ProcedureModel(name="DMLS CROWN", price=3000, gap_days=3, total_sittings=2),
            ProcedureModel(name="ZIRCONIA CROWN 2", price=4000, gap_days=3, total_sittings=2),
            ProcedureModel(name="ZIRCONIA 5", price=5000, gap_days=3, total_sittings=2),
            ProcedureModel(name="ZIRCONIA 10", price=6000, gap_days=3, total_sittings=2),
            ProcedureModel(name="COMPLETE DENTURE", price=10000, gap_days=3, total_sittings=5),
            ProcedureModel(name="RPD", price=500, gap_days=3, total_sittings=2),
            ProcedureModel(name="VENEER", price=5000, gap_days=3, total_sittings=2),
            ProcedureModel(name="LOCAL IMPLANT", price=15000, gap_days=7, total_sittings=3),
            ProcedureModel(name="KOREAN IMPLANT", price=25000, gap_days=7, total_sittings=3),
            ProcedureModel(name="PREMIUM DENTURE", price=20000, gap_days=3, total_sittings=5),
            ProcedureModel(name="ALIGNER", price=70000, gap_days=7, total_sittings=4)
        ]
        db.add_all(defaults)
        db.commit()
        procs = db.query(ProcedureModel).all()
        
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "gap_days": p.gap_days,
            "total_sittings": p.total_sittings
        }
        for p in procs
    ]

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
    
    referral_leads = sum(1 for p in patients if p.source == "Referral")
    insta_leads = sum(1 for p in patients if p.source == "Insta")
    google_leads = sum(1 for p in patients if p.source == "Google")
    walkin_leads = sum(1 for p in patients if p.source == "Walkin")
    
    return {
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "total_dues": total_dues,
        "referral_leads": referral_leads,
        "insta_leads": insta_leads,
        "google_leads": google_leads,
        "walkin_leads": walkin_leads
    }

@app.get("/views/appointments")
def get_appointments(db: Session = Depends(get_db)):
    today = date.today()
    patients = db.query(PatientModel).all()
    
    today_list = []
    future_list = []
    scaling_recall_list = []
    
    six_months_ago = today - timedelta(days=180)
    
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        proc_name = proc.name if proc else "General"
        
        wa_text = f"Hello {p.patient_name}, reminder for your dental appointment at SRA Dental Clinic today at {p.time_slot}."
        wa_link = f"https://wa.me/91{p.phone_number}?text={wa_text.replace(' ', '%20')}" if p.phone_number else ""
        
        item = {
            "opd_number": p.opd_number,
            "patient_name": p.patient_name,
            "phone": p.phone_number,
            "patient_place": p.patient_place,
            "procedure": proc_name,
            "time_slot": p.time_slot,
            "pending_payment": p.payment_left,
            "whatsapp_link": wa_link,
            "next_appointment": p.next_appointment.isoformat() if p.next_appointment else None,
            "source": p.source
        }
        
        if p.next_appointment == today:
            today_list.append(item)
        elif p.next_appointment and p.next_appointment > today:
            future_list.append(item)
            
        if proc_name == "SCALING" and p.created_date <= six_months_ago:
            scale_text = f"Hello {p.patient_name}, it has been 6 months since your last scaling at SRA Dental Clinic. Time for a routine check-up and scaling!"
            scale_link = f"https://wa.me/91{p.phone_number}?text={scale_text.replace(' ', '%20')}" if p.phone_number else ""
            scaling_recall_list.append({
                "opd_number": p.opd_number,
                "patient_name": p.patient_name,
                "phone": p.phone_number,
                "patient_place": p.patient_place,
                "last_date": p.created_date.isoformat(),
                "whatsapp_link": scale_link
            })
            
    return {"today": today_list, "future": future_list, "scaling_recall": scaling_recall_list}

class PatientCreate(BaseModel):
    patient_name: str
    phone_number: str
    patient_place: str = ""
    procedure_id: int
    time_slot: str
    payment_done: float
    discount: float = 0.0
    next_appointment: Optional[str] = None
    source: str = "Walkin"

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
        source=data.source
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
        raise HTTPException(status_code=404, detail="Patient not found")
        
    if data.next_appointment:
        appt_date = datetime.strptime(data.next_appointment, "%Y-%m-%d").date()
        if appt_date.weekday() == 6:
            raise HTTPException(status_code=400, detail="Sunday is reserved for new patients only, no follow-ups allowed!")

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
            (PatientModel.patient_place.contains(search)) |
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
            "patient_place": p.patient_place,
            "procedure": proc.name if proc else "General",
            "current_sitting": p.current_sitting,
            "total_sittings": p.total_sittings,
            "base_price": p.base_price,
            "discount": p.discount,
            "total_amount": p.total_amount,
            "total_paid": p.total_paid,
            "payment_left": p.payment_left,
            "next_appointment": p.next_appointment.isoformat() if p.next_appointment else None,
            "source": p.source
        })
    return logs
