import { configureStore } from "@reduxjs/toolkit";
import toggleReducer from "./toggleSlice";

export const store = configureStore({
    reducer: {
        toggleStream: toggleReducer,
    },
});

// typescript type exports
    // AppState = type of the entire Redux state tree! Also commonly called RootState
    // AppDispatch = type of the dispatch function of the state
export type AppState = ReturnType<typeof store.getState>;
export type AppDispatch = ReturnType<typeof store.dispatch>;