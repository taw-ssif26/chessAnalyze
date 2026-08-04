'use client';

import React from 'react';
import { Chessboard } from 'react-chessboard';
import { useChessStore } from '../store/useChessStore';

export const ChessBoardContainer: React.FC = () => {
  const { fen, history, currentIndex, setCurrentIndex } = useChessStore();

  const handleNext = () => {
    if (currentIndex < history.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > -1) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  return (
    <div className="flex flex-col items-center gap-4 bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-2xl">
      <div className="w-[450px] aspect-square rounded-lg overflow-hidden">
        <Chessboard 
          position={fen} 
          arePiecesDraggable={false} // Analysis board viewer settings
          customBoardStyle={{
            borderRadius: '8px',
            boxShadow: '0 5px 15px rgba(0, 0, 0, 0.5)'
          }}
          customDarkSquareStyle={{ backgroundColor: '#769656' }}
          customLightSquareStyle={{ backgroundColor: '#eeeed2' }}
        />
      </div>
      
      <div className="flex gap-4 w-full justify-center">
        <button 
          onClick={handlePrev}
          disabled={currentIndex <= -1}
          className="px-6 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition disabled:opacity-40"
        >
          Previous
        </button>
        <button 
          onClick={handleNext}
          disabled={currentIndex >= history.length - 1}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
};
