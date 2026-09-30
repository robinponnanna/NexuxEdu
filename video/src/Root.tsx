import React from "react";
import { Composition } from "remotion";
import { MicroLessonComposition } from "./compositions/MicroLessonComposition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MicroLesson"
        component={MicroLessonComposition}
        durationInFrames={5400} // Default 180s @ 30fps
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          lesson: {
            title: "Demystifying Paging, Page Tables & The TLB Hit/Miss Cycle",
            subject_code: "CS301",
            co_code: "CO3",
            scenes: [
              {
                scene_id: 1,
                title: "The Memory Virtualization Illusion",
                duration_seconds: 35,
                type: "concept",
                narration: "Modern operating systems give every process its own private, isolated virtual address space.",
                key_takeaway: "Virtual addresses split into Page Number and Offset."
              }
            ]
          }
        }}
      />
    </>
  );
};
