import { configureStore } from '@reduxjs/toolkit';
import kpiReducer from './kpiSlice';

export const store = configureStore({
  reducer: {
    kpi: kpiReducer,
  },
});
