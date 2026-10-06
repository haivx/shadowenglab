import { LessonStatus } from "@shadowenglab/contracts";

export default function Home() {
  return (
    <main data-lesson-statuses={LessonStatus.options.length}>
      <h1>ShadowEngLab</h1>
    </main>
  );
}
