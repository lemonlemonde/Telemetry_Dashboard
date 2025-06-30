'use client';
// custom button component that uses the toggle action for Redux


// import the toggle redux action
import { toggleStream } from '../store/toggleSlice';
// import the types that you defined in store.ts
import { AppState, AppDispatch } from '../store/store';

// import Redux funcs that make subscribed components and dispatch actions
import { useSelector, useDispatch } from 'react-redux';


function ToggleButton() {
    // type check!
    const dispatch = useDispatch<AppDispatch>();

    // get subscribed component
    const isStreaming = useSelector((state: AppState) => state.toggleStream.isStreaming);

    return (
        <button onClick={() => dispatch(toggleStream())}>
            {isStreaming ? 'Stop Streaming' : 'Start Streaming'}
        </button>
    );
}

export default ToggleButton;