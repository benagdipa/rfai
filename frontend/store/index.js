import { configureStore, combineReducers } from '@reduxjs/toolkit';
import {
  persistStore,
  persistReducer,
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
} from 'redux-persist';
import storage from 'redux-persist/lib/storage'; // LocalStorage for persistence
import kpiReducer from './kpiSlice';
import authReducer from './authSlice'; // New reducer for auth state
import uiReducer from './uiSlice'; // New reducer for UI state
import logger from 'redux-logger'; // Middleware for action logging

// Persist configuration
const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth'], // Persist only auth state
};

// Root reducer combining all slices
const rootReducer = combineReducers({
  kpi: kpiReducer,
  auth: authReducer,
  ui: uiReducer,
});

// Persisted reducer
const persistedReducer = persistReducer(persistConfig, rootReducer);

// Configure the store
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore redux-persist actions for serialization checks
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }).concat(process.env.NODE_ENV === 'development' ? logger : []), // Add logger in dev mode
  devTools: process.env.NODE_ENV !== 'production', // Enable Redux DevTools in dev mode
});

// Persistor for persisting state
export const persistor = persistStore(store);

// Types for TypeScript (optional)
// export type RootState = ReturnType<typeof store.getState>;
// export type AppDispatch = typeof store.dispatch;