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
import { createLogger } from 'redux-logger';
import kpiReducer from './kpiSlice';
import authReducer from './authSlice';
import uiReducer from './uiSlice';

// Conditional storage import for client-side only
const isClient = typeof window !== 'undefined';

const storage = isClient ? require('redux-persist/lib/storage').default : null;

// No-op storage for server-side
const noopStorage = {
  getItem: () => Promise.resolve(null),
  setItem: () => Promise.resolve(),
  removeItem: () => Promise.resolve(),
};

// Persistence configuration
const persistConfig = {
  key: 'root',
  storage: isClient ? storage : noopStorage,
  whitelist: ['auth'], // Persist only auth slice
};

// Debug logging for storage choice
console.log('Using storage:', isClient ? 'localStorage' : 'noopStorage');

// Combine reducers
const rootReducer = combineReducers({
  kpi: kpiReducer,
  auth: authReducer,
  ui: uiReducer,
});

// Apply persistence to root reducer
const persistedReducer = persistReducer(persistConfig, rootReducer);

// Create custom logger middleware
const loggerMiddleware = createLogger({
  collapsed: true, // Collapse logs by default
  diff: true, // Show state diffs for easier debugging
});

// Configure the Redux store
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER], // Ignore persistence actions
      },
    }).concat(process.env.NODE_ENV === 'development' ? loggerMiddleware : []),
  devTools: process.env.NODE_ENV !== 'production', // Enable Redux DevTools in dev
});

// Create persistor for redux-persist
export const persistor = persistStore(store);

// Log persistor state for debugging
persistor.subscribe(() => {
  console.log('Persistor state:', persistor.getState());
});