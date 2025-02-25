import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  drawerOpen: false,
  themeMode: 'light', // 'light' | 'dark'
  notifications: [],
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleDrawer(state) {
      state.drawerOpen = !state.drawerOpen;
    },
    setThemeMode(state, action) {
      state.themeMode = action.payload;
    },
    addNotification(state, action) {
      state.notifications.push({
        id: Date.now(),
        message: action.payload.message,
        severity: action.payload.severity || 'info', // 'success' | 'info' | 'warning' | 'error'
      });
    },
    removeNotification(state, action) {
      state.notifications = state.notifications.filter((n) => n.id !== action.payload);
    },
  },
});

export const { toggleDrawer, setThemeMode, addNotification, removeNotification } = uiSlice.actions;
export default uiSlice.reducer;