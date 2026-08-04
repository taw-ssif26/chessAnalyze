'use client';

import React from 'react';
import { useChessStore } from '../store/useChessStore';

export const MoveList: React.FC = () => {
  const { history, currentIndex, setCurrentIndex } = useChessStore();

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'Brilliant': return 'bg-emerald-500 text-white';
      case 'Excellent': return 'bg-teal-600 text-white';
      case 'Good': return 'bg-blue-600 text-white';
      case 'Inaccuracy': return 'bg-yellow-600 text-white';
      case 'Mistake': return 'bg-orange-600 text-white';
      case 'Blunder': return 'bg-red-600 text-white';
      default: return 'bg-slate-700 text-slate-200';
    }
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-4 h-[300px] flex flex-col">
      <h3 className="text-sm font-semibold text-slate-400 mb-2 uppercase tracking-wider">Move Log</h3>
      <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-2 content-start pr-1">
        {history.map((move, index) => (
          <button
            key={index}
            onClick={() => setCurrentIndex(index)}
            className={`flex justify-between items-center px-3 py-2 rounded-lg text-sm font-medium transition ${
              currentIndex === index 
                ? 'bg-indigo-600/30 border border-indigo-500 text-white' 
                : 'bg-slate-800/50 border border-transparent text-slate-300 hover:bg-slate-800'
            }`}
          >
            <span>{move.move_number}. {move.san}</span>
            <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${getQualityColor(move.move_quality)}`}>
              {move.move_quality}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
