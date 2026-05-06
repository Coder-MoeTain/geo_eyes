import { defineComponent } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../stores/intel", () => {
  const store = {
    detections: [],
    uploadedTileUrl: "http://tiles/uploaded/{z}/{x}/{y}.png",
    uploadAndDetect: vi.fn().mockResolvedValue({ image_id: 42, task_id: "task-1" }),
    loadUploadedTileUrl: vi.fn().mockResolvedValue("http://tiles/uploaded/{z}/{x}/{y}.png"),
  };
  return { useIntelStore: () => store };
});

describe("UploadDetectPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders uploaded raster tile overlay through IntelMap", async () => {
    const IntelMapStub = defineComponent({
      props: ["rasterTilesUrl"],
      template: `<div data-test="map-url">{{ rasterTilesUrl || '' }}</div>`,
    });
    const page = await import("../UploadDetectPage.vue");
    const wrapper = mount(page.default, {
      global: {
        stubs: { IntelMap: IntelMapStub },
      },
    });
    expect(wrapper.get('[data-test="map-url"]').text()).toContain("http://tiles/uploaded/{z}/{x}/{y}.png");
  });
});
