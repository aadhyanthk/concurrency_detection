import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [seats, setSeats] = useState([]);
  const [attackResults, setAttackResults] = useState([]);
  const [isAttacking, setIsAttacking] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Modal & Timer States
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [timeLeft, setTimeLeft] = useState(0);

  const fetchSeats = async () => {
    try {
      const res = await fetch('/api/seats');
      const data = await res.json();
      setSeats(data);
      setLoading(false);
    } catch (err) {
      console.error("Fetch failed", err);
    }
  };

  useEffect(() => {
    fetchSeats();
    // Background polling every 3 seconds
    const interval = setInterval(fetchSeats, 3000);
    return () => clearInterval(interval);
  }, []);

  // Timer logic for the Modal: Syncs UI and Backend Release
  useEffect(() => {
    let timer;
    if (timeLeft > 0) {
      timer = setInterval(() => setTimeLeft(prev => prev - 1), 1000);
    } else if (timeLeft === 0 && selectedSeat) {
      // TRIGGER: When timer hits zero, close modal and refresh grid immediately
      setSelectedSeat(null);
      fetchSeats(); 
    }
    return () => clearInterval(timer);
  }, [timeLeft, selectedSeat]);

  const handleHold = async (id, label) => {
    try {
      const res = await fetch(`/api/seats/${id}/hold`, { method: 'POST' });
      if (res.status === 409) {
        alert("Seat already held or booked!");
        return;
      }
      setSelectedSeat({ id, label });
      setTimeLeft(120); // Initialize 2-minute countdown
      fetchSeats();
    } catch (err) {
      console.error("Error holding seat", err);
    }
  };

  const handlePayment = async () => {
    try {
      const res = await fetch(`/api/seats/${selectedSeat.id}/book`, { method: 'POST' });
      if (res.ok) {
        alert(`Seat ${selectedSeat.label} successfully booked!`);
        setSelectedSeat(null);
        fetchSeats();
      } else {
        alert("Payment failed: Hold might have expired.");
      }
    } catch (err) {
      console.error("Payment error", err);
    }
  };

  // Simulation: Fast forward BOTH frontend and backend TTL
  const runTimeout = async () => {
    try {
      // 1. Tell the backend to expire the seat immediately
      await fetch(`/api/seats/${selectedSeat.id}/timeout`, { method: 'POST' });
      
      // 2. Sync the frontend timer to 3 seconds for visual impact
      setTimeLeft(3);
    } catch (err) {
      console.error("Failed to fast-forward TTL", err);
    }
  };

  const runAttack = async (mode) => {
    setIsAttacking(true);
    setAttackResults([]);
    const seatId = 1; // Target Seat A1 for Benchmarking
    
    const requests = Array.from({ length: 10 }).map(async () => {
      const url = mode === 'pessimistic' 
        ? `/api/seats/${seatId}/hold` 
        : `/api/simulate/${mode}/${seatId}`;
        
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      
      return {
        success: res.ok,
        message: data.message || data.detail || (res.ok ? "Success" : "Conflict Detected")
      };
    });

    const results = await Promise.all(requests);
    setAttackResults(results);
    setIsAttacking(false);
    fetchSeats();
  };

  const handleReset = async () => {
    await fetch('/api/seed', { method: 'POST' });
    setSelectedSeat(null);
    fetchSeats();
  };

  if (loading) return <div className="cinema-container">Initializing System...</div>;

  return (
    <div className="cinema-container">
      <h1>Cinema Concurrency Lab</h1>
      
      <div className="main-layout">
        {/* Left Panel: The Theatre Grid */}
        <div className="panel">
          <h2>Theatre Grid</h2>
          <div className="screen"></div>
          <div className="grid">
            {seats.map((seat) => (
              <div
                key={seat.id}
                className={`seat ${seat.status}`}
                onClick={() => seat.status === 'AVAILABLE' && handleHold(seat.id, seat.seat_label)}
              >
                {seat.seat_label}
              </div>
            ))}
          </div>
          <button onClick={handleReset}>Reset Theatre</button>
        </div>

        {/* Right Panel: The Concurrency Arena */}
        <div className="panel">
          <h2>Race Condition Arena (Target: A1)</h2>
          <div className="attack-buttons">
            <button className="danger" onClick={() => runAttack('unsafe')} disabled={isAttacking}>
              Unsafe Attack
            </button>
            <button className="warning" onClick={() => runAttack('pessimistic')} disabled={isAttacking}>
              Pessimistic Attack
            </button>
            <button className="safe" onClick={() => runAttack('optimistic')} disabled={isAttacking}>
              Optimistic Attack
            </button>
          </div>
          
          <div className="results-log">
            {isAttacking ? <p>Simulating Concurrent Requests...</p> : 
              attackResults.map((res, i) => (
                <div key={i} className={`log-entry ${res.success ? 'success' : 'fail'}`}>
                  User {i+1}: {res.message}
                </div>
              ))
            }
          </div>
        </div>
      </div>

      {/* PAYMENT MODAL with Timer Sync */}
      {selectedSeat && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Confirm Booking: {selectedSeat.label}</h3>
            <p className="timer">
              Time Remaining: {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, '0')}
            </p>
            
            <div className="modal-actions">
              <button className="safe" onClick={handlePayment}>Complete Payment</button>
              <button className="warning" onClick={runTimeout}>Run Time Out</button>
              <button className="danger" onClick={() => setSelectedSeat(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;