"use client";

import { Provider } from "react-redux"
import { store } from "@/store/store";
import React from "react";

// https://stackoverflow.com/questions/77393577/redux-in-nextjs-13-approuter-pattern-minimizing-use-client
export default function ReduxProvider({children}: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;

};
