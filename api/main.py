import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Load environment variables from the .env file
load_dotenv()

# Retrieve and validate the database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

# Initialize the synchronous SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Seat schema for the database
class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="AVAILABLE") # States: AVAILABLE, HELD, BOOKED
    hold_expiry = Column(DateTime, nullable=True)
    version = Column(Integer, default=1) # Required for Optimistic Locking

# Initialize the FastAPI application
app = FastAPI(title="Concurrency Cinema API")

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ensure tables are created upon server startup
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

# Standard health check endpoint
@app.get("/")
def read_root():
    return {"status": "Online", "database": "Connected"}