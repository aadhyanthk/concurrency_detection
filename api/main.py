import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import timedelta

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

# Initialize the synchronous SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Correct Seat schema
class Seat(Base):
    __tablename__ = "seats"
    id = Column(Integer, primary_key=True, index=True) 
    seat_label = Column(String) 
    status = Column(String, default="AVAILABLE") 
    hold_expiry = Column(DateTime, nullable=True)
    version = Column(Integer, default=1)

app = FastAPI(title="Concurrency Cinema API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    # TEMPORARY: Uncomment the line below, run the server ONCE to fix the schema, 
    # then comment it back out to prevent data loss in the future.
    # Base.metadata.drop_all(bind=engine) 
    
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"status": "Online", "database": "Connected"}

@app.post("/seed")
def seed_theatre(db: Session = Depends(get_db)):
    """Initializes or Resets 100 seats to AVAILABLE status."""
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    seats_per_row = 10
    
    existing_count = db.query(Seat).count()
    
    if existing_count == 0:
        new_seats = []
        seat_id = 1
        for row in rows:
            for num in range(1, seats_per_row + 1):
                new_seats.append(Seat(
                    id=seat_id,
                    seat_label=f"{row}{num}",
                    status="AVAILABLE",
                    version=1
                ))
                seat_id += 1
        db.add_all(new_seats)
    else:
        db.query(Seat).update({
            "status": "AVAILABLE",
            "hold_expiry": None,
            "version": 1
        })
    
    db.commit()
    return {"message": "Theatre grid initialized successfully", "total_seats": 100}

@app.get("/seats")
def get_seats(db: Session = Depends(get_db)):
    return db.query(Seat).order_by(Seat.id).all()

@app.post("/seats/{seat_id}/hold")
def hold_seat(seat_id: int, db: Session = Depends(get_db)):
    """
    Attempts to put a 2-minute hold on a seat.
    Uses pessimistic locking to prevent race conditions during the hold phase.
    """
    # 1. Start a transaction and lock the row
    # 'with_for_update' tells Postgres: "I am modifying this, nobody else touch it yet."
    seat = db.query(Seat).with_for_update().filter(Seat.id == seat_id).first()

    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    now = datetime.utcnow()

    # 2. Check if the seat is actually available
    # A seat is available if status is 'AVAILABLE' OR if the hold has expired
    is_expired = seat.hold_expiry and now > seat.hold_expiry
    
    if seat.status == "AVAILABLE" or (seat.status == "HELD" and is_expired):
        # 3. Apply the hold
        seat.status = "HELD"
        seat.hold_expiry = now + timedelta(minutes=2)
        db.commit()
        return {
            "message": f"Seat {seat.seat_label} is now held for 2 minutes",
            "expiry": seat.hold_expiry
        }
    else:
        db.rollback()
        raise HTTPException(status_code=409, detail="Seat is already taken or held by someone else")

@app.post("/seats/{seat_id}/book")
def book_seat(seat_id: int, db: Session = Depends(get_db)):
    """
    Finalizes the booking. Only works if the seat is currently HELD and not expired.
    """
    seat = db.query(Seat).with_for_update().filter(Seat.id == seat_id).first()
    
    now = datetime.utcnow()
    
    if seat and seat.status == "HELD" and now <= seat.hold_expiry:
        seat.status = "BOOKED"
        seat.hold_expiry = None # Clear expiry once fully booked
        db.commit()
        return {"message": f"Seat {seat.seat_label} booked successfully"}
    
    db.rollback()
    raise HTTPException(status_code=400, detail="Hold expired or seat unavailable")

@app.post("/simulate/unsafe/{seat_id}")
async def simulate_unsafe_booking(seat_id: int, db: Session = Depends(get_db)):
    """
    DELIBERATELY UNSAFE: Demonstrates a race condition.
    No locking is used, allowing double-bookings to occur.
    """
    # 1. Fetch the seat status (Read)
    seat = db.query(Seat).filter(Seat.id == seat_id).first()

    if not seat or seat.status != "AVAILABLE":
        return {"success": False, "message": "Seat already taken (Detected at Read)"}

    # 2. Artificial Delay
    # This creates a window where another thread can read the same "AVAILABLE" state.
    await asyncio.sleep(0.5) 

    # 3. Update the seat (Write)
    seat.status = "BOOKED"
    db.commit()

    return {"success": True, "message": f"Seat {seat.seat_label} booked (Unsafely)"}

@app.post("/simulate/optimistic/{seat_id}")
async def simulate_optimistic_booking(seat_id: int, db: Session = Depends(get_db)):
    """
    OPTIMISTIC LOCKING: Uses the version column to detect concurrent changes.
    High performance, but users will see "Conflict" errors under heavy load.
    """
    # 1. Read current state and version
    seat = db.query(Seat).filter(Seat.id == seat_id).first()

    if not seat or seat.status != "AVAILABLE":
        return {"success": False, "message": "Seat already taken (Detected at Read)"}

    current_version = seat.version

    # 2. Artificial Delay (Simulating work/lag)
    await asyncio.sleep(0.5)

    # 3. Targeted Update (The 'Version Check')
    # We update ONLY if the version hasn't changed since we read it.
    result = db.query(Seat).filter(
        Seat.id == seat_id, 
        Seat.version == current_version
    ).update({
        "status": "BOOKED",
        "version": Seat.version + 1 # Increment version for the next person
    })

    db.commit()

    if result == 0:
        # result == 0 means no row matched the ID + Version combo.
        # This implies someone else changed the row while we were sleeping.
        return {
            "success": False, 
            "message": "Concurrency Conflict: Someone else booked this seat first!"
        }

    return {"success": True, "message": f"Seat {seat.seat_label} booked (Optimistically)"}