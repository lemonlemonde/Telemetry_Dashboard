import { createSlice } from '@reduxjs/toolkit';

interface ToggleState {
    isStreaming: boolean;
};

const initialState: ToggleState = {
    isStreaming: false
};


// make the slice
const toggleSlice = createSlice({
    name: 'streamToggle', 
    initialState,
    reducers: {
        toggleStream: (state) => {
            state.isStreaming = !state.isStreaming;
        },
    },
});

export default toggleSlice.reducer;
export const { toggleStream } = toggleSlice.actions;