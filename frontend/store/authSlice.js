import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  user: null,
  status: 'idle', // 'idle' | 'loading' | 'succeeded' | 'failed'
  error: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setUser(state, action) {
      state.user = action.payload;
      state.status = 'succeeded';
      state.error = null;
    },
    clearUser(state) {
      state.user = null;
      state.status = 'idle';
      state.error = null;
    },
    setAuthLoading(state) {
      state.status = 'loading';
      state.error = null;
    },
    setAuthError(state, action) {
      state.status = 'failed';
      state.error = action.payload;
    },
  },
});

export const { setUser, clearUser, setAuthLoading, setAuthError } = authSlice.actions;
export default authSlice.reducer;