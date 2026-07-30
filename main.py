from datetime import date, datetime
from typing import Optional
import os
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
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
    total_sittings = Column(Integer, default=1)

class PatientModel(Base):
    __tablename__ = "patients"
    opd_number = Column(String, primary_key=True, index=True)
    patient_name = Column(String)
    phone_number = Column(String)
    procedure_id = Column(Integer)
    base_price = Column(Float, default=0.0)
    total_amount = Column(Float)
    total_paid = Column(Float, default=0.0)
    payment_left = Column(Float)
    time_slot = Column(String)
    created_date = Column(Date, default=date.today)

class EndoChartModel(Base):
    __tablename__ = "endo_charts"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, index=True)
    tooth_number = Column(String)
    canals_data = Column(Text)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SRA Dental Clinic API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/")
def serve_patient_portal(): return FileResponse("patient.html")

@app.get("/admin")
def serve_admin_portal(): return FileResponse("index.html")

@app.get("/procedures")
def get_procedures(db: Session = Depends(get_db)):
    procs = db.query(ProcedureModel).all()
    if not procs:
        db.add_all([
            ProcedureModel(name="RCT ANTERIOR", price=2000), ProcedureModel(name="RCT POSTERIOR", price=2500),
            ProcedureModel(name="CONSULTATION", price=100), ProcedureModel(name="EXTRACTION", price=500)
        ])
        db.commit()
        procs = db.query(ProcedureModel).all()
    return [{"id": p.id, "name": p.name, "price": p.price} for p in procs]

class PatientCreate(BaseModel):
    patient_name: str
    phone_number: str
    procedure_id: int
    time_slot: str
    payment_done: float

@app.post("/patients")
def create_patient(data: PatientCreate, db: Session = Depends(get_db)):
    count = db.query(PatientModel).count() + 1
    opd_number = f"OPD-{100 + count}"
    proc = db.query(ProcedureModel).filter(ProcedureModel.id == data.procedure_id).first()
    
    base_amt = proc.price if proc else 0.0
    payment_left = max(0.0, base_amt - data.payment_done)

    new_patient = PatientModel(
        opd_number=opd_number, patient_name=data.patient_name, phone_number=data.phone_number,
        procedure_id=data.procedure_id, base_price=base_amt, total_amount=base_amt,
        total_paid=data.payment_done, payment_left=payment_left, time_slot=data.time_slot
    )
    db.add(new_patient)
    db.commit()
    return {"message": "Success", "opd_number": opd_number}

@app.get("/patients/{opd_number}")
def get_patient_details(opd_number: str, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    proc = db.query(ProcedureModel).filter(ProcedureModel.id == patient.procedure_id).first()
    return {
        "opd_number": patient.opd_number,
        "patient_name": patient.patient_name,
        "procedure_name": proc.name if proc else "General"
    }

class EndoSaveRequest(BaseModel):
    opd_number: str
    tooth_number: str
    canals_data: str

@app.post("/patients/endo-chart")
def save_endo_chart(data: EndoSaveRequest, db: Session = Depends(get_db)):
    chart = db.query(EndoChartModel).filter(EndoChartModel.opd_number == data.opd_number, EndoChartModel.tooth_number == data.tooth_number).first()
    if chart:
        chart.canals_data = data.canals_data
    else:
        chart = EndoChartModel(opd_number=data.opd_number, tooth_number=data.tooth_number, canals_data=data.canals_data)
        db.add(chart)
    db.commit()
    return {"message": "Saved successfully"}

@app.post("/patients/{opd_number}/upload-treatment-file")
async def upload_treatment_file(opd_number: str, file_type: str = Form(...), tooth_number: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_path = f"uploads/{opd_number}_Tooth_{tooth_number}_{file_type}_{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    return {"message": f"Uploaded successfully"}

@app.get("/views/daily-log")
def daily_log(db: Session = Depends(get_db)):
    patients = db.query(PatientModel).all()
    logs = []
    for p in patients:
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == p.procedure_id).first()
        logs.append({
            "opd_number": p.opd_number, "patient_name": p.patient_name,
            "procedure": proc.name if proc else "General",
            "total_amount": p.total_amount, "total_paid": p.total_paid
        })
    return reversed(logs)
