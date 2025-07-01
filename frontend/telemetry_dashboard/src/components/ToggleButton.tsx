// custom button component that uses the toggle action for Redux
'use client';

// import the toggle redux action
import { toggleStream } from '../store/toggleSlice';
// import the types that were defined in store.ts
import { AppState, AppDispatch } from '../store/store';

// import Redux funcs that make subscribed components and dispatch actions
import { useSelector, useDispatch } from 'react-redux'


function ToggleButton() {
    // type check!
    const dispatch = useDispatch<AppDispatch>();

    // get subscribed component
    const isStreaming = useSelector((state: AppState) => state.toggleStream.isStreaming);

    return (
        <div>
            <button className="border-2 border-pink-200 p-5 rounded-[20px] cursor-pointer hover:bg-pink-950" onClick={() => dispatch(toggleStream())}>
                {isStreaming ? 'Stop Streaming' : 'Start Streaming'}
            </button>
        </div>
    );
}

export default ToggleButton;