import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

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