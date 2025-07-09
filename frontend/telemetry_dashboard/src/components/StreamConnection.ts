"use client";

import { useEffect, useRef, RefObject, SetStateAction } from "react";
import { useSelector, useDispatch } from "react-redux";
import { toggleStream } from '../store/toggleSlice';
import { AppState } from '../store/store';


export function StreamConnection(
    url: RefObject<HTMLInputElement | null>,
    client_id: RefObject<HTMLInputElement | null>,
    setUserMsg: React.Dispatch<SetStateAction<string>>,
    onMessage: (event: MessageEvent) => void
) {
    // get subscribed component
    const isStreaming = useSelector((state: AppState) => state.toggleStream.isStreaming);
    
    const ws = useRef<WebSocket | null>(null);
    const dispatch = useDispatch<AppDispatch>();

    const errorOccurred = useRef<boolean>(false);

    useEffect(() => {
        console.log("Reconfiguring ws as needed! Cur isStreaming:", isStreaming);
        // clear msg
        // setUserMsg("<3");

        if (isStreaming) {
            // want to start streaming
            try {

                const url_constructed = `${url.current?.value}?client_id=${client_id.current?.value}`;
                console.log("Trying to connect to url:", url_constructed);


                ws.current = new WebSocket(url_constructed);
                
                ws.current.onopen = () => {
                    console.log("Stream connected!");
                    setUserMsg("Stream connected!");
                };
                
                ws.current.onmessage = (event: MessageEvent) => {
                    onMessage(event.data);
                    // setUserMsg(event.data);
                };
                
                ws.current.onclose = (event: CloseEvent) => {
                    if (!errorOccurred.current) {
                        // if no error, user toggle button themselves.
                        console.log("Stream disconnected. Bye! <3");
                        setUserMsg("Stream disconnected. Bye! <3");
                    }
                    errorOccurred.current = false;
                };
                
                ws.current.onerror = (error: Event) => {
                    errorOccurred.current = true;
                    console.error(`Oh no! D: Stream disconnected. WebSocket error: ${error.type}`);
                    setUserMsg(`Oh no! D: Stream disconnected. WebSocket error: ${error.type}`);
                    // if error, user didn't toggle button themselves, and we need to handle it
                    dispatch(toggleStream());
                };
            } catch (e) {
                setUserMsg(e as string)
            }
        } else {
            // want to stop streaming!
            ws.current?.close();
            // setUserMsg("Stream successfully stopped.")
        }

        // clean up
        return () => {
            ws.current?.close();
        };

    }, [isStreaming]);

}


