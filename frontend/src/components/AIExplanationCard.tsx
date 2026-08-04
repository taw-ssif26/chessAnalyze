'use client';

import React from 'react';
import { useChessStore } from '../store/useChessStore';
import { Sparkles } from 'lucide-react';

export const AIExplanationCard: React.FC = () => {
  const { history, currentIndex } = useChessStore();
  const currentMove = currentIndex >= 0 ? history[currentIndex] : null;

  return (
    <div className="w-full bg-slate-950 border border-indigo-900/40 rounded-2xl p-6 relative overflow-hidden shadow-xl">
      <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-3xl pointer-events-none rounded-full" />
      
      <div className="flex items-center gap-2 text-indigo-400 mb-4">
        <Sparkles size={18} className="animate-pulse" />
        <h3 className="text-sm font-bold uppercase tracking-widest">Coaching Insights</h3>
      </div>

      {currentMove ? (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4 text-xs text-slate-400 border-b border-slate-800/60 pb-3">
            <div>Played Move: <span className="font-bold text-white">{currentMove.san}</span></div>
            <div>Evaluation After: <span className="font-bold text-white">{currentMove.evaluation_after}</span></div>
            <div>Optimal Engine Selection: <span className="font-bold text-white text-emerald-400">{currentMove.best_move}</span></div>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed font-normal whitespace-pre-line">
            {currentMove.ai_explanation}
          </p>
        </div>
      ) : (
        <div className="flex items-center justify-center h-28">
          <p className="text-sm text-slate-500 italic">Select a completed move to view step-by-step master-level strategy explanation.</p>
        </div>
      )}
    </div>
  );
};
