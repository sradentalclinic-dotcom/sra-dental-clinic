from datetime import date, datetime
from typing import Optional, List
import os
import json
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import Column, Date, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

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
    age = Column(Integer, nullable=True)
    phone_number = Column(String)
    patient_place = Column(String, default="Mandi Dabwali")
    procedure_id = Column(Integer)
    units = Column(Integer, default=1)
    total_sittings = Column(Integer, default=1)
    current_sitting = Column(Integer, default=1)
    base_price = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    total_amount = Column(Float)
    total_paid = Column(Float, default=0.0)
    payment_left = Column(Float)
    time_slot = Column(String)
    next_appointment = Column(Date, nullable=True)
    next_appointment_time = Column(String, nullable=True)
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
    canals_data = Column(Text)

class LabWorkModel(Base):
    __tablename__ = "lab_works"
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String, index=True)
    patient_name = Column(String)
    lab_item = Column(String)
    units = Column(Integer, default=1)
    cost_per_unit = Column(Float)
    total_lab_cost = Column(Float)
    lab_name = Column(String, default="Premier Dental Lab")
    status = Column(String, default="Sent to Lab")
    payment_status = Column(String, default="Pending")
    created_date = Column(Date, default=date.today)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SRA Dental Modern Operatory Suite")
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
    return FileResponse("index.html")

@app.get("/admin")
def serve_admin_portal():
    return FileResponse("index.html")

# FULL UPDATED PRICE LIST LOADED INTO DATABASE
@app.get("/procedures")
def get_procedures(db: Session = Depends(get_db)):
    procs = db.query(ProcedureModel).all()
    
    # Updated Price List Sync
    price_list = [
        ("RCT ANTERIOR", 2000, 3, 3),
        ("RCT POSTERIOR", 2500, 3, 3),
        ("RCT PEDO", 2000, 3, 2),
        ("CONSULTATION", 100, 0, 1),
        ("TEMPORARY FILLING", 100, 0, 1),
        ("GIC FILLING", 500, 0, 1),
        ("COMPOSITE FILLING", 1000, 0, 1),
        ("EXTRACTION", 500, 2, 1),
        ("SURGICAL EXTRACTION", 3000, 3, 2),
        ("SCALING", 1000, 0, 1),
        ("METAL CROWN", 1500, 3, 2),
        ("PFM CROWN", 2000, 3, 2),
        ("PREMIUM PFM CROWN", 2500, 3, 2),
        ("DMLS CROWN", 3000, 3, 2),
        ("ZIRCONIA CROWN 2", 4000, 3, 2),
        ("ZIRCONIA 5", 5000, 3, 2),
        ("ZIRCONIA 10", 6000, 3, 2),
        ("COMPLETE DENTURE", 10000, 5, 3),
        ("RPD", 500, 3, 2),
        ("VENEER", 5000, 3, 2),
        ("LOCAL IMPLANT", 15000, 7, 3),
        ("KOREAN IMPLANT", 25000, 7, 3),
        ("PREMIUM DENTURE", 20000, 5, 3)
    ]

    if not procs:
        defaults = [ProcedureModel(name=item[0], price=item[1], gap_days=item[2], total_sittings=item[3]) for item in price_list]
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
    
    lab_orders = db.query(LabWorkModel).all()
    total_lab_dues = sum(l.total_lab_cost for l in lab_orders if l.payment_status == "Pending")

    return {
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "total_dues": total_dues,
        "today_opd": today_opd,
        "total_opd": len(patients),
        "total_lab_dues": total_lab_dues,
        "reel_leads": sum(1 for p in patients if p.source == "Instagram Reel"),
        "web_leads": sum(1 for p in patients if p.source == "Website")
    }

class PatientCreate(BaseModel):
    patient_name: str
    age: Optional[int] = None
    phone_number: str
    patient_place: Optional[str] = "Mandi Dabwali"
    procedure_id: int
    units: int = 1
    time_slot: Optional[str] = "10:00"
    payment_done: float = 0.0
    discount: float = 0.0
    next_appointment: Optional[str] = None
    next_appointment_time: Optional[str] = None
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
    units_cnt = max(1, data.units)
    
    # Auto calculation: (Base Price * Units) - Discount
    total_amt = max(0.0, (base_amt * units_cnt) - data.discount)
    payment_left = max(0.0, total_amt - data.payment_done)

    next_date = None
    if data.next_appointment and data.next_appointment.strip():
        try:
            next_date = datetime.strptime(data.next_appointment.strip(), "%Y-%m-%d").date()
        except ValueError:
            next_date = None

    new_patient = PatientModel(
        opd_number=opd_number,
        patient_name=data.patient_name,
        age=data.age,
        phone_number=data.phone_number,
        patient_place=data.patient_place or "Mandi Dabwali",
        procedure_id=data.procedure_id,
        units=units_cnt,
        total_sittings=proc.total_sittings if proc else 1,
        base_price=base_amt,
        discount=data.discount,
        total_amount=total_amt,
        total_paid=data.payment_done,
        payment_left=payment_left,
        time_slot=data.time_slot or "10:00",
        next_appointment=next_date,
        next_appointment_time=data.next_appointment_time,
        source=data.source,
        extracted_tooth=data.extracted_tooth,
        operatory_chair=data.operatory_chair,
        medical_alerts=data.medical_alerts
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return {"message": "Patient registered successfully", "opd_number": opd_number}

class PatientUpdate(BaseModel):
    patient_name: Optional[str] = None
    age: Optional[int] = None
    phone_number: Optional[str] = None
    patient_place: Optional[str] = None
    procedure_id: Optional[int] = None
    units: Optional[int] = None
    time_slot: Optional[str] = None
    payment_done: Optional[float] = None
    discount: Optional[float] = None
    next_appointment: Optional[str] = None
    next_appointment_time: Optional[str] = None
    operatory_chair: Optional[str] = None

@app.put("/patients/{opd_number}")
def update_patient(opd_number: str, data: PatientUpdate, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")
    
    if data.patient_name is not None: patient.patient_name = data.patient_name
    if data.age is not None: patient.age = data.age
    if data.phone_number is not None: patient.phone_number = data.phone_number
    if data.patient_place is not None: patient.patient_place = data.patient_place
    if data.operatory_chair is not None: patient.operatory_chair = data.operatory_chair
    if data.units is not None: patient.units = max(1, data.units)
    if data.time_slot is not None: patient.time_slot = data.time_slot
    if data.next_appointment_time is not None: patient.next_appointment_time = data.next_appointment_time
    
    if data.procedure_id is not None and data.procedure_id > 0:
        patient.procedure_id = data.procedure_id
        proc = db.query(ProcedureModel).filter(ProcedureModel.id == data.procedure_id).first()
        if proc:
            patient.base_price = proc.price
            patient.total_sittings = proc.total_sittings

    if data.discount is not None: patient.discount = data.discount
    if data.payment_done is not None: patient.total_paid = data.payment_done
    
    # Recalculate billing automatically
    patient.total_amount = max(0.0, (patient.base_price * patient.units) - patient.discount)
    patient.payment_left = max(0.0, patient.total_amount - patient.total_paid)

    if data.next_appointment is not None:
        if data.next_appointment.strip():
            try:
                patient.next_appointment = datetime.strptime(data.next_appointment.strip(), "%Y-%m-%d").date()
            except ValueError:
                patient.next_appointment = None
        else:
            patient.next_appointment = None

    db.commit()
    return {"message": "Patient updated successfully"}

@app.delete("/patients/{opd_number}")
def delete_patient(opd_number: str, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")
    
    db.query(EndoChartModel).filter(EndoChartModel.opd_number == opd_number).delete()
    db.query(LabWorkModel).filter(LabWorkModel.opd_number == opd_number).delete()
    db.delete(patient)
    db.commit()
    return {"message": f"Patient {opd_number} permanently deleted"}

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
        "age": patient.age,
        "phone_number": patient.phone_number,
        "patient_place": patient.patient_place,
        "procedure_id": patient.procedure_id,
        "procedure_name": proc.name if proc else "General",
        "units": patient.units,
        "base_price": patient.base_price,
        "total_amount": patient.total_amount,
        "total_paid": patient.total_paid,
        "payment_left": patient.payment_left,
        "discount": patient.discount,
        "source": patient.source,
        "operatory_chair": patient.operatory_chair,
        "medical_alerts": patient.medical_alerts,
        "next_appointment": patient.next_appointment.isoformat() if patient.next_appointment else None,
        "next_appointment_time": patient.next_appointment_time,
        "charts": saved_charts
    }

# LAB WORK RATES & BILLING
LAB_RATES = {
    "PFM": 350.0,
    "Zirconia": 900.0,
    "Denture": 1100.0,
    "Metal Cap": 150.0,
    "RPD": 50.0
}

@app.get("/lab-rates")
def get_lab_rates():
    return LAB_RATES

class LabWorkCreate(BaseModel):
    opd_number: str
    lab_item: str
    units: int = 1
    lab_name: Optional[str] = "Premier Dental Lab"

@app.post("/lab-orders")
def create_lab_order(data: LabWorkCreate, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.opd_number == data.opd_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient OPD number not found")

    cost_per_unit = LAB_RATES.get(data.lab_item, 0.0)
    units_cnt = max(1, data.units)
    total_lab_cost = cost_per_unit * units_cnt

    lab_order = LabWorkModel(
        opd_number=data.opd_number,
        patient_name=patient.patient_name,
        lab_item=data.lab_item,
        units=units_cnt,
        cost_per_unit=cost_per_unit,
        total_lab_cost=total_lab_cost,
        lab_name=data.lab_name or "Premier Dental Lab",
        status="Sent to Lab",
        payment_status="Pending"
    )
    db.add(lab_order)
    db.commit()
    db.refresh(lab_order)
    return {"message": "Lab Work order added successfully", "order_id": lab_order.id}

@app.get("/lab-orders")
def list_lab_orders(db: Session = Depends(get_db)):
    orders = db.query(LabWorkModel).order_by(LabWorkModel.id.desc()).all()
    return [{
        "id": o.id,
        "opd_number": o.opd_number,
        "patient_name": o.patient_name,
        "lab_item": o.lab_item,
        "units": o.units,
        "cost_per_unit": o.cost_per_unit,
        "total_lab_cost": o.total_lab_cost,
        "lab_name": o.lab_name,
        "status": o.status,
        "payment_status": o.payment_status,
        "date": o.created_date.isoformat() if o.created_date else None
    } for o in orders]

@app.put("/lab-orders/{order_id}")
def update_lab_order(order_id: int, status: Optional[str] = None, payment_status: Optional[str] = None, db: Session = Depends(get_db)):
    order = db.query(LabWorkModel).filter(LabWorkModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    if status: order.status = status
    if payment_status: order.payment_status = payment_status
    db.commit()
    return {"message": "Lab order updated successfully"}

@app.delete("/lab-orders/{order_id}")
def delete_lab_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(LabWorkModel).filter(LabWorkModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    db.delete(order)
    db.commit()
    return {"message": "Lab order removed"}

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
    canals_data: str

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
            "age": p.age,
            "phone": p.phone_number,
            "patient_place": p.patient_place,
            "procedure": proc.name if proc else "General",
            "units": p.units,
            "time_slot": p.time_slot,
            "pending_payment": p.payment_left,
            "operatory_chair": p.operatory_chair,
            "next_appointment": p.next_appointment.isoformat() if p.next_appointment else None,
            "next_appointment_time": p.next_appointment_time
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
            "age": p.age,
            "phone": p.phone_number,
            "patient_place": p.patient_place,
            "procedure": proc.name if proc else "General",
            "units": p.units,
            "current_sitting": p.current_sitting,
            "total_sittings": p.total_sittings,
            "total_amount": p.total_amount,
            "total_paid": p.total_paid,
            "payment_left": p.payment_left,
            "source": p.source,
            "chair": p.operatory_chair
        })
    return list(reversed(logs))
