"use client";

import { useState, useRef } from "react";

import ToggleButton from "./ToggleButton";
import { StreamConnection } from "./StreamConnection";

const postLatency = async (data: number) => {
    const response = await fetch("http://127.0.0.1:8000/latency", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ 'latency': data }),
    });

    const result = await response.json();
    console.log(result);
};

export default function StreamButton() {

    const [userMsg, setUserMsg] = useState("<3");
    const url = useRef<HTMLInputElement | null>(null);
    const client_id = useRef<HTMLInputElement | null>(null);

    // var latency_total = 0
    // var msg_count = 0

    const onMessage = (event: MessageEvent) => {
        const telem_dict = JSON.parse(String(event));
        setUserMsg(event);

        const time_sent = Date.parse(telem_dict['reading_timestamp']);
        const time_received = Date.now();

        const time_diff_s = (time_received - time_sent) / 1000;
        console.log("Latency:", time_diff_s);

        // latency_total += time_diff_s;
        // msg_count += 1;

        // const latency_avg = latency_total / msg_count;
        // console.log("Avg Latency:", latency_avg)
        
        // POST this back to backend.py
        postLatency(time_diff_s)
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