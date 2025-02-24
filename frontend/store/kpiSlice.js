import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../lib/api';

export const fetchKpiData = createAsyncThunk('kpi/fetch', async (identifier) => {
  const monitor = await api.get(`/monitor/${identifier}`);
  const predict = await api.get(`/predict/${identifier}`);
  return { monitor, predict };
});

const kpiSlice = createSlice({
  name: 'kpi',
  initialState: { data: null, eda: null, status: 'idle', error: null },
  reducers: {
    updateEda(state, action) {
      state.eda = action.payload;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchKpiData.pending, (state) => { state.status = 'loading'; })
      .addCase(fetchKpiData.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.data = action.payload;
      })
      .addCase(fetchKpiData.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.error.message;
      });
  },
});

export const { updateEda } = kpiSlice.actions;
export default kpiSlice.reducer;
