import React from 'react';

export default function Overview() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">MRO Dashboard</h1>
          <p className="text-slate-500 mt-1">WINNIIO design system - Next.js Migration (Task M5)</p>
        </div>
      </header>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Cells</p>
          <p className="text-3xl font-extrabold text-slate-900 mt-2">75</p>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Handover Success Rate</p>
          <p className="text-3xl font-extrabold text-teal-600 mt-2">99.99%</p>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Ping-Pong Rate</p>
          <p className="text-3xl font-extrabold text-green-600 mt-2">0.00%</p>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Status</p>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 mt-2">
            SLA Compliant
          </span>
        </div>
      </div>
    </div>
  );
}
