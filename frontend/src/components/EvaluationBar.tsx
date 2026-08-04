import React from 'react';
import { useChessStore } from '../store/useChessStore';

export const EvaluationBar: React.FC = () => {
  const { history, currentIndex } = useChessStore();
  const currentMove = currentIndex >= 0 ? history[currentIndex] : null;

  const getPercentage = () => {
    if (!currentMove) return 50; // Equal game state initial setting

    const evalStr = currentMove.evaluation_after;
    if (evalStr.startsWith('M')) {
      // Mate evaluation sizing configuration
      return evalStr.includes('-') ? 0 : 100;
    }

    const value = parseFloat(evalStr);
    if (isNaN(value)) return 50;

    // Map evaluation ranges from -5 to +5 dynamically to percentage metrics
    const clamped = Math.max(-5, Math.min(5, value));
    return ((clamped + 5) / 10) * 100;
  };

  const percentage = getPercentage();

  return (
    <div className="w-8 h-full bg-slate-800 rounded-lg overflow-hidden flex flex-col relative border border-slate-700">
      <div 
        className="w-full bg-white transition-all duration-500 ease-out" 
        style={{ height: `${100 - percentage}%` }} 
      />
      <div 
        className="w-full bg-slate-900 transition-all duration-500 ease-out" 
        style={{ height: `${percentage}%` }} 
      />
      <span className="absolute left-1/2 -translate-x-1/2 top-4 text-xs font-black mix-blend-difference text-white">
        {currentMove ? currentMove.evaluation_after : "0.0"}
      </span>
    </div>
  );
};
