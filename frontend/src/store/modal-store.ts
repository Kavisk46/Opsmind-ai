import { create } from "zustand";

interface ModalState {
  activeModalId: string | null;
  modalProps: Record<string, unknown> | undefined;
  openModal: (id: string, props?: Record<string, unknown>) => void;
  closeModal: () => void;
}

// Generic, ID-based modal manager — any feature opens a modal through this
// one store instead of getting a dedicated store of its own.
export const useModalStore = create<ModalState>((set) => ({
  activeModalId: null,
  modalProps: undefined,
  openModal: (id, props) => set({ activeModalId: id, modalProps: props }),
  closeModal: () => set({ activeModalId: null, modalProps: undefined }),
}));
