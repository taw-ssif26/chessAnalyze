import { create } from 'zustand';

export interface MoveAnalysis {
  move_number: number;
  san: string;
  uci: string;
  fen: string;
  evaluation_before: string;
  evaluation_after: string;
  best_move: string;
  principal_variation: string[];
  move_quality: string;
  ai_explanation: string;
}

interface ChessStore {
  fen: string;
  history: MoveAnalysis[];
  currentIndex: number;
  isLoading: boolean;
  setAnalysisData: (moves: MoveAnalysis[]) => void;
  setCurrentIndex: (index: number) => void;
  setIsLoading: (loading: boolean) => void;
}

export const useChessStore = create<ChessStore>((set) => ({
  fen: "start",
  history: [],
  currentIndex: -1,
  isLoading: false,
  setAnalysisData: (moves) => set({ 
    history: moves, 
    currentIndex: moves.length > 0 ? 0 : -1,
    fen: moves.length > 0 ? moves[0].fen : "start"
  }),
  setCurrentIndex: (index) => set((state) => {
    if (index >= 0 && index < state.history.length) {
      return { currentIndex: index, fen: state.history[index].fen };
    }
    if (index === -1) {
      return { currentIndex: -1, fen: "start" };
    }
    return {};
  }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
