'use client';

import React, { useState } from 'react';
import { ChessBoardContainer } from '../../components/ChessBoardContainer';
import { EvaluationBar } from '../../components/EvaluationBar';
import { MoveList } from '../../components/MoveList';
import { AIExplanationCard } from '../../components/AIExplanationCard';
import { useChessStore } from '../../store/useChessStore';

export default function AnalyzePage() {
  const [pgnInput, setPgnInput] = useState('');
  const { setAnalysisData, isLoading, setIsLoading } = useChessStore();

  const handleImport = async () => {
    if (!pgnInput.trim()) return;
    setIsLoading(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/import-pgn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pgn: pgnInput }),
      });

      if (!response.ok) throw new Error('Failed to analyze selected PGN');
      
      const payload = await response.json();
      
      // Pull evaluation response
      const analysisResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/analysis/${payload.analysis_id}`);
      const data = await analysisResponse.json();
      
      setAnalysisData(data.moves);
    } catch (err) {
      alert("Error: Ensure your backend system is running, the PGN data structure is valid, and keys are loaded.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col font-sans">
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur sticky top-0 z-50 px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center font-bold text-white text-lg">♔</div>
          <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">AI Chess Coach</span>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Control Panel / Input Form */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-white">Upload New Match</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Paste standard PGN coordinates directly to generate move classifications and retrieve AI evaluation explanations.
            </p>
            <textarea
              className="w-full h-36 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono focus:border-indigo-500 focus:outline-none text-slate-300 resize-none"
              placeholder="1. e4 e5 2. Nf3 Nc6 3. Bb5 a6..."
              value={pgnInput}
              onChange={(e) => setPgnInput(e.target.value)}
            />
            <button
              onClick={handleImport}
              disabled={isLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 px-4 rounded-xl transition duration-200 shadow-md text-sm disabled:opacity-50"
            >
              {isLoading ? "Analyzing positions..." : "Start Analysis"}
            </button>
          </div>
          
          <MoveList />
        </div>

        {/* Center & Right Column Board Viewer + AI Engine Output */}
        <div className="lg:col-span-8 flex flex-col md:flex-row gap-6 items-stretch">
          <div className="flex gap-4 items-stretch justify-center">
            <EvaluationBar />
            <ChessBoardContainer />
          </div>
          
          <div className="flex-1 flex flex-col">
            <AIExplanationCard />
          </div>
        </div>
      </main>
    </div>
  );
}
