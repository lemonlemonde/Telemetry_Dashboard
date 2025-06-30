import Image from "next/image";
import ToggleButton from "@/components/ToggleButton";

export default function Home() {
  return (
    <div className="grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-[32px] row-start-2 items-center sm:items-start">
        <p className="text-red-100 text-9xl">{"<3"}</p>
        <ToggleButton/>
      </main>
      <footer className="row-start-3 flex gap-[24px] flex-wrap items-center justify-center">
        <p>{"<3"}</p>
      </footer>
    </div>
  );
}
