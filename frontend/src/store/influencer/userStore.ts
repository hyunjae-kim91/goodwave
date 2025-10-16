import { create } from 'zustand';

interface UserState {
  selectedUser: string | null;
  setSelectedUser: (username: string | null) => void;
}

export const useUserStore = create<UserState>((set: any) => ({
  selectedUser: null,
  setSelectedUser: (username: string | null) => set({ selectedUser: username }),
}));
