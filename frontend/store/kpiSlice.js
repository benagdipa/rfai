import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../lib/api';

export const fetchKpiData = createAsyncThunk(
  'kpi/fetchKpiData',
  async (identifier, { rejectWithValue }) => {
    try {
      const [monitorResponse, predictResponse, issuesResponse, optimizationResponse] = await Promise.all([
        api.get(`/monitor/${identifier}`),
        api.get(`/predict/${identifier}`),
        api.get(`/issues/${identifier}`),
        api.get(`/optimize/${identifier}`),
      ]);

      return {
        monitor: monitorResponse.data,
        predict: predictResponse.data,
        issues: issuesResponse.data,
        optimization: optimizationResponse.data,
      };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch KPI data';
      console.error('Fetch KPI data error:', { message: errorMessage, status: error.response?.status });
      return rejectWithValue(errorMessage);
    }
  }
);

const initialState = {
  data: {
    monitor: null,
    predict: null,
    issues: null,
    optimization: null,
  },
  eda: null,
  status: 'idle', // 'idle' | 'loading' | 'succeeded' | 'failed'
  error: null,
};

const kpiSlice = createSlice({
  name: 'kpi',
  initialState,
  reducers: {
    updateEda(state, action) {
      state.eda = action.payload;
      state.status = 'succeeded';
      state.error = null;
    },
    updateDataSection(state, action) {
      const { section, data } = action.payload;
      if (Object.keys(state.data).includes(section)) {
        state.data[section] = data;
        state.status = 'succeeded';
        state.error = null;
      } else {
        console.warn(`Invalid data section: ${section}`);
      }
    },
    clearData(state) {
      state.data = initialState.data;
      state.eda = null;
      state.status = 'idle';
      state.error = null;
    },
    setLoading(state) {
      state.status = 'loading';
      state.error = null;
    },
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
        state.data = { ...state.data, ...action.payload };
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

export const selectKpiData = (state) => state.kpi.data;
export const selectEda = (state) => state.kpi.eda;
export const selectKpiStatus = (state) => state.kpi.status;
export const selectKpiError = (state) => state.kpi.error;