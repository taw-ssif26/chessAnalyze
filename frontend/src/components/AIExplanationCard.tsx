'use client';

import React, { useEffect, useState } from 'react';
import { useChessStore } from '../store/useChessStore';
import { Sparkles, Loader2 } from 'lucide-react';

export const AIExplanationCard: React.FC = () => {
  const { history, currentIndex, setAnalysisData } = useChessStore();
  const currentMove = currentIndex >= 0 ? history[currentIndex] : null;
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);

  useEffect(() => {
    if (!currentMove) {
      setExplanation(null);
      return;
    }

    // Read directly if already computed
    if (currentMove.ai_explanation) {
      setExplanation(currentMove.ai_explanation);
      return;
    }

    const fetchExplanationOnDemand = async () => {
      setLoading(true);
      setExplanation(null);
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/move/${currentMove.id}/explain`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' } }
        );

        if (!response.ok) throw new Error('API Error');

        const data = await response.json();
        setExplanation(data.explanation);

        // Update the local Zustand store cache to preserve computed state
        const updatedHistory = [...history];
        updatedHistory[currentIndex] = {
          ...currentMove,
          ai_explanation: data.explanation,
        };
        setAnalysisData(updatedHistory);
      } catch (err) {
        setExplanation("Unable to generate analysis insights. Verify network configuration and API keys.");
      } finally {
        setLoading(false);
      }
    };

    fetchExplanationOnDemand();
  }, [currentIndex, currentMove, history, setAnalysisData]);

  return (
    <div className="w-full bg-slate-950 border border-indigo-900/40 rounded-2xl p-6 relative overflow-hidden shadow-xl min-h-[220px] flex flex-col justify-between">
      <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-3xl pointer-events-none rounded-full" />
      
      <div>
        <div className="flex items-center gap-2 text-indigo-400 mb-4">
          <Sparkles size={18} className="animate-pulse" />
          <h3 className="text-sm font-bold uppercase tracking-widest">Coaching Insights</h3>
        </div>

        {currentMove ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-4 text-xs text-slate-400 border-b border-slate-800/60 pb-3">
              <div>Move: <span className="font-bold text-white">{currentMove.san}</span></div>
              <div>Eval: <span className="font-bold text-white">{currentMove.evaluation_after}</span></div>
              <div>Best Choice: <span className="font-bold text-white text-emerald-400">{currentMove.best_move}</span></div>
            </div>

            {loading ? (
              <div className="flex flex-col gap-2 py-4 justify-center items-center text-slate-400">
                <Loader2 className="animate-spin text-indigo-500" size={24} />
                <span className="text-xs italic">Analyzing positional logic...</span>
              </div>
            ) : (
              <p className="text-sm text-slate-300 leading-relaxed font-normal whitespace-pre-line animate-fade-in">
                {explanation}
              </p>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-28">
            <p className="text-sm text-slate-500 italic">Select a move to view detailed coaching analysis.</p>
          </div>
        )}
      </div>
    </div>
  );
};
