import React, { useState, useEffect } from 'react';
import { Folder, Calendar, Trash2, ArrowLeft, Clock, Monitor, User, Activity, Download, ShieldAlert } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const API_BASE = "http://localhost:8000";

export default function App() {
  const [employees, setEmployees] = useState([]);
  const [selectedEmp, setSelectedEmp] = useState(null);
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [dayData, setDayData] = useState({ screenshots: [], logs: [] });

  useEffect(() => {
    fetch(`${API_BASE}/api/employees`)
      .then(res => res.json())
      .then(data => setEmployees(data))
      .catch(err => console.error(err));
  }, []);

  const handleSelectEmp = (emp) => {
    setSelectedEmp(emp);
    setSelectedDate(null);
    fetch(`${API_BASE}/api/employees/${emp}/dates`)
      .then(res => res.json())
      .then(data => setDates(data));
  };

  const handleSelectDate = (date) => {
    setSelectedDate(date);
    fetch(`${API_BASE}/api/data/${selectedEmp}/${date}`)
      .then(res => res.json())
      .then(data => setDayData(data));
  };

  const handleDeleteDate = (date) => {
    if (window.confirm(`Delete records for ${date}?`)) {
      fetch(`${API_BASE}/api/delete/${selectedEmp}/${date}`, { method: 'DELETE' })
        .then(() => {
          setDates(dates.filter(d => d !== date));
          if (selectedDate === date) setSelectedDate(null);
        });
    }
  };

  // Export Logs to CSV
  const exportToCSV = () => {
    if (!dayData.logs.length) return;
    const csvContent = "data:text/csv;charset=utf-8," + dayData.logs.map(e => e.replace(/,/g, " ")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${selectedEmp}_${selectedDate}_report.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const calculateStats = () => {
    let productive = 0, nonProductive = 0, idle = 0;
    dayData.logs.forEach(log => {
      if (log.includes("Category: Productive")) productive++;
      else if (log.includes("Category: Non-Productive")) nonProductive++;
      else if (log.includes("Category: Idle")) idle++;
    });
    return [
      { name: 'Productive', value: productive || 1, color: '#10B981' },
      { name: 'Non-Productive', value: nonProductive, color: '#EF4444' },
      { name: 'Idle', value: idle, color: '#F59E0B' }
    ];
  };

  return (
    <div style={{ backgroundColor: '#FAFAFA', minHeight: '100vh', fontFamily: "'Inter', sans-serif", color: '#18181B' }}>
      <header style={{ backgroundColor: '#FFFFFF', borderBottom: '1px solid #E4E4E7', padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: '#2563EB', padding: '8px', borderRadius: '10px', color: '#FFF' }}>
            <Activity size={20} />
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: '700' }}>Admin Dashboard</h1>
        </div>
        {selectedEmp && (
          <button 
            onClick={() => { setSelectedEmp(null); setSelectedDate(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', borderRadius: '8px', backgroundColor: '#F4F4F5', border: '1px solid #E4E4E7', cursor: 'pointer', fontWeight: '500' }}
          >
            <ArrowLeft size={16} /> Back to Directory
          </button>
        )}
      </header>

      <main style={{ padding: '32px', maxWidth: '1280px', margin: '0 auto' }}>
        
        {/* DIRECTORY VIEW */}
        {!selectedEmp && (
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '600', color: '#71717A', marginBottom: '20px' }}>Employee Directory</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '20px' }}>
              {employees.map(emp => (
                <div 
                  key={emp} 
                  onClick={() => handleSelectEmp(emp)}
                  style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '16px', border: '1px solid #E4E4E7', cursor: 'pointer', textAlign: 'center' }}
                >
                  <div style={{ width: '56px', height: '56px', borderRadius: '50%', backgroundColor: '#EFF6FF', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                    <User size={28} color="#2563EB" />
                  </div>
                  <h3 style={{ fontWeight: '600', fontSize: '16px' }}>{emp}</h3>
                  <span style={{ fontSize: '12px', color: '#10B981', marginTop: '4px', display: 'block' }}>● System Protected</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* DATES VIEW */}
        {selectedEmp && !selectedDate && (
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '20px' }}>
              Work Records for <span style={{ color: '#2563EB' }}>{selectedEmp}</span>
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '16px' }}>
              {dates.map(date => (
                <div 
                  key={date}
                  style={{ backgroundColor: '#FFFFFF', padding: '16px 20px', borderRadius: '12px', border: '1px solid #E4E4E7', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <div onClick={() => handleSelectDate(date)} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px', flexGrow: 1 }}>
                    <Calendar size={20} color="#10B981" />
                    <span style={{ fontWeight: '500' }}>{date}</span>
                  </div>
                  <button onClick={() => handleDeleteDate(date)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#EF4444' }}>
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* DETAILS VIEW */}
        {selectedEmp && selectedDate && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <button onClick={() => setSelectedDate(null)} style={{ border: 'none', background: 'none', color: '#2563EB', fontWeight: '500', cursor: 'pointer' }}>
                ← Back to Dates
              </button>
              <button onClick={exportToCSV} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', backgroundColor: '#10B981', color: 'white', borderRadius: '8px', border: 'none', cursor: 'pointer', fontWeight: '600' }}>
                <Download size={16} /> Export Payroll CSV
              </button>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '2.5fr 1fr', gap: '24px' }}>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>Screenshots ({selectedDate})</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '16px' }}>
                  {dayData.screenshots.map((shot, idx) => (
                    <div key={idx} style={{ backgroundColor: '#FFFFFF', borderRadius: '12px', overflow: 'hidden', border: '1px solid #E4E4E7' }}>
                      <img src={`${API_BASE}${shot.url}`} alt="shot" style={{ width: '100%', height: '140px', objectFit: 'cover' }} />
                      <div style={{ padding: '10px', fontSize: '12px', color: '#71717A', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={12} /> {shot.time}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ backgroundColor: '#FFFFFF', padding: '20px', borderRadius: '16px', border: '1px solid #E4E4E7' }}>
                  <h3 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '16px' }}>Productivity Stats</h3>
                  <div style={{ height: '180px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={calculateStats()} dataKey="value" cx="50%" cy="50%" innerRadius={45} outerRadius={65}>
                          {calculateStats().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div style={{ backgroundColor: '#FFFFFF', padding: '20px', borderRadius: '16px', border: '1px solid #E4E4E7' }}>
                  <h3 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '16px' }}>Activity Logs</h3>
                  <div style={{ maxHeight: '280px', overflowY: 'auto', fontSize: '12px' }}>
                    {dayData.logs.map((log, index) => (
                      <div key={index} style={{ padding: '8px 0', borderBottom: '1px solid #F4F4F5' }}>
                        {log}
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}