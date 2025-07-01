"use client";

import { useState, useRef } from "react";

import ToggleButton from "./ToggleButton";
import { StreamConnection } from "./StreamConnection";

export default function StreamButton() {

    const [userMsg, setUserMsg] = useState("<3");
    const url = useRef<HTMLInputElement | null>(null);
    const client_id = useRef<HTMLInputElement | null>(null);

    const onMessage = (event: MessageEvent) => {
        // TODO: do something
        console.log("Received telemetry!!");
    };

    const stream_conn = StreamConnection(url, client_id, setUserMsg, onMessage);
    return (
        <div className="flex flex-col space-y-8">
            <div>
                <p>websocket endpoint</p>
                <input className="border-2 border-pink-200 p-2 rounded-[10pt]" defaultValue={"http://127.0.0.1:8000/ws"} ref={url}></input>
            </div>
            <div>
                <p>client id</p>
                <input className="border-2 border-pink-200 p-2 rounded-[10pt]" defaultValue={"dashboard_uwu"} ref={client_id}></input>
            </div>
            <ToggleButton/>
            <p>{userMsg}</p>
        </div>
    );
}