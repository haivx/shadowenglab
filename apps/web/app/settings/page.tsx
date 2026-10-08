"use client";

import { AppHeader } from "@/components/AppHeader";
import { KeyField } from "@/components/KeyField";
import { MicSection } from "@/components/MicSection";
import { ModelStatusList } from "@/components/ModelStatusList";
import { PracticeDefaults } from "@/components/PracticeDefaults";

/** S8 Settings (UI-SPEC): các mục trong một cột max-width 860. */
export default function SettingsPage() {
  return (
    <>
      <AppHeader />
      <main className="mx-auto flex max-w-[860px] flex-col gap-5 p-8">
        <h1 className="text-[34px] font-extrabold leading-tight tracking-[-0.03em]">
          Settings
        </h1>
        <KeyField />
        <PracticeDefaults />
        <MicSection />
        <ModelStatusList />
      </main>
    </>
  );
}
