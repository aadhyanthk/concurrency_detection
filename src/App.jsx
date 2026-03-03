import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [seats, setSeats] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchSeats = async () => {
    try {
      const res = await fetch('/api/seats');
      const data = await res.json();
      setSeats(data);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch seats", err);
    }
  };

  useEffect(() => {
    fetchSeats();
    // Poll for updates every 3 seconds to reflect holds/bookings from other "users"
    const interval = setInterval(fetchSeats, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleHold = async (id) => {
    try {
      const res = await fetch(`/api/seats/${id}/hold`, { method: 'POST' });
      if (res.status === 409) {
        alert("Seat already held or booked!");
      }
      fetchSeats();
    } catch (err) {
      console.error("Error holding seat", err);
    }
  };

  const handleReset = async () => {
    await fetch('/api/seed', { method: 'POST' });
    fetchSeats();
  };

  if (loading) return <div className="cinema-container">Initializing System...</div>;

  return (
    <div className="cinema-container">
      <h1>Cinema Concurrency Lab</h1>
      <div className="screen"></div>
      
      <div className="grid">
        {seats.map((seat) => (
          <div
            key={seat.id}
            className={`seat ${seat.status}`}
            onClick={() => seat.status === 'AVAILABLE' && handleHold(seat.id)}
          >
            {seat.seat_label}
          </div>
        ))}
      </div>

      <div className="controls">
        <button onClick={handleReset}>Reset Theatre</button>
      </div>
    </div>
  );
}

export default App;