import { create } from 'zustand';
import { AppState } from '../../types/influencer';

export const useAppStore = create<AppState>((set: any, get: any) => ({
  // 초기 상태
  activeMainTab: 'influencer-exploration',
  activeSubTab: 'campaign-collection',
  sessionId: undefined,
  profile: undefined,
  posts: [],
  
  loading: {
    ingest: false,
    explore: false,
    classification: false,
    category: false,
    'overall-analysis': false,
  },
  
  // 액션들
  setActiveMainTab: (tab: any) => set({ activeMainTab: tab }),
  
  setActiveSubTab: (tab: any) => set({ activeSubTab: tab }),
  
  setIngestData: (sessionId: any, profile: any, posts: any) => set({
    sessionId,
    profile,
    posts,
  }),
  
  setLoading: (type: any, value: any) => set((state: any) => ({
    loading: {
      ...state.loading,
      [type]: value,
    },
  })),
  
  reset: () => set({
    activeMainTab: 'influencer-exploration',
    activeSubTab: 'campaign-collection',
    sessionId: undefined,
    profile: undefined,
    posts: [],
    loading: {
      ingest: false,
      explore: false,
      classification: false,
      category: false,
      'overall-analysis': false,
    },
  }),
})); 