import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../lib/api';

// Async thunk to fetch KPI data
export const fetchKpiData = createAsyncThunk(
  'kpi/fetchKpiData',
  async (identifier, { rejectWithValue }) => {
    try {
      const [monitorResponse, predictResponse, issuesResponse, optimizationResponse] = await Promise.all([
        api.get(`/monitor/${identifier}`),
        api.get(`/predict/${identifier}`),
        api.get(`/issues/${identifier}`), // New endpoint for issues
        api.get(`/optimize/${identifier}`), // New endpoint for optimization
      ]);

      return {
        monitor: monitorResponse.data,
        predict: predictResponse.data,
        issues: issuesResponse.data,
        optimization: optimizationResponse.data,
      };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch KPI data';
      console.error('Fetch KPI data error:', errorMessage);
      return rejectWithValue(errorMessage);
    }
  }
);

// Initial state with expanded structure
const initialState = {
  data: {
    monitor: null, // KPI monitoring data
    predict: null, // Prediction data
    issues: null, // Issues data
    optimization: null, // Optimization proposals
  },
  eda: null, // EDA insights
  status: 'idle', // 'idle' | 'loading' | 'succeeded' | 'failed'
  error: null, // Error message
};

// KPI slice
const kpiSlice = createSlice({
  name: 'kpi',
  initialState,
  reducers: {
    // Update EDA from WebSocket or manual action
    updateEda(state, action) {
      state.eda = action.payload;
      state.status = 'succeeded';
      state.error = null;
    },
    // Update specific data section manually
    updateDataSection(state, action) {
      const { section, data } = action.payload; // e.g., { section: 'monitor', data: {...} }
      if (Object.keys(state.data).includes(section)) {
        state.data[section] = data;
        state.status = 'succeeded';
        state.error = null;
      } else {
        console.warn(`Invalid data section: ${section}`);
      }
    },
    // Clear all data
    clearData(state) {
      state.data = initialState.data;
      state.eda = null;
      state.status = 'idle';
      state.error = null;
    },
    // Set loading state manually
    setLoading(state) {
      state.status = 'loading';
      state.error = null;
    },
    // Set error state manually
    setError(state, action) {
      state.status = 'failed';
      state.error = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchKpiData.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(fetchKpiData.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.data = {
          ...state.data, // Preserve existing data not updated
          ...action.payload, // Merge new data
        };
        state.error = null;
      })
      .addCase(fetchKpiData.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
      });
  },
});

export const { updateEda, updateDataSection, clearData, setLoading, setError } = kpiSlice.actions;
export default kpiSlice.reducer;

// Selector helpers
export const selectKpiData = (state) => state.kpi.data;
export const selectEda = (state) => state.kpi.eda;
export const selectKpiStatus = (state) => state.kpi.status;
export const selectKpiError = (state) => state.kpi.error;

// Types for TypeScript (optional)
// export type KpiState = ReturnType<typeof kpiSlice.reducer>;