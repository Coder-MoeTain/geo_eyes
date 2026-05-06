import { defineComponent } from "vue";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("axios", () => ({
  default: {
    create: () => ({
      interceptors: {
        response: {
          use: vi.fn(),
        },
      },
      get: getMock,
      post: postMock,
    }),
  },
}));

describe("ImageryViewerPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    getMock.mockReset();
    postMock.mockReset();
    localStorage.clear();
  });

  it("saves AOI and refreshes AOI list from API", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [] } });
    getMock.mockResolvedValueOnce({
      data: { items: [{ id: 7, name: "Saved AOI", geojson: { type: "Polygon", coordinates: [[[90, 23], [91, 23], [91, 24], [90, 23]]] } }] },
    });
    postMock.mockResolvedValueOnce({ data: { id: 7, name: "Saved AOI" } });

    const IntelMapStub = defineComponent({
      emits: ["update:aoi"],
      template: `<button data-test="emit-aoi" @click="$emit('update:aoi', { type: 'Polygon', coordinates: [[[90,23],[91,23],[91,24],[90,23]]] })">emit</button>`,
    });

    const page = await import("../ImageryViewerPage.vue");
    const wrapper = mount(page.default, {
      global: {
        stubs: {
          IntelMap: IntelMapStub,
        },
      },
    });

    await wrapper.get('[data-test="emit-aoi"]').trigger("click");
    const saveBtn = wrapper
      .findAll("button")
      .find((b) => b.text().includes("Save AOI"));
    expect(saveBtn).toBeTruthy();
    await saveBtn!.trigger("click");

    expect(postMock).toHaveBeenCalledWith(
      "/api/v1/aoi",
      expect.objectContaining({ name: expect.any(String), geojson: expect.objectContaining({ type: "Polygon" }) }),
      expect.any(Object),
    );
    expect(getMock).toHaveBeenCalledTimes(2);
  });

  it("loads last AOI from localStorage", async () => {
    localStorage.setItem("geoeye:lastAOI", JSON.stringify({ type: "Polygon", coordinates: [[[90, 23], [91, 23], [91, 24], [90, 23]]] }));
    getMock.mockResolvedValueOnce({ data: { items: [] } });

    const page = await import("../ImageryViewerPage.vue");
    const wrapper = mount(page.default, {
      global: {
        stubs: { IntelMap: true },
      },
    });

    expect(wrapper.text()).toContain("Polygon");
  });
});
