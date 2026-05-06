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

describe("HistoricalComparisonPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    getMock.mockReset();
    postMock.mockReset();
  });

  it("loads split tile URLs and passes them to IntelMap", async () => {
    getMock
      .mockResolvedValueOnce({
        data: { items: [{ id: 11, filename: "before.tif" }, { id: 12, filename: "after.tif" }] },
      })
      .mockResolvedValueOnce({ data: { tiles_url: "http://tiles/before/{z}/{x}/{y}.png" } })
      .mockResolvedValueOnce({ data: { tiles_url: "http://tiles/after/{z}/{x}/{y}.png" } });

    const IntelMapStub = defineComponent({
      props: ["enableCompare", "compareLeftTilesUrl", "compareRightTilesUrl"],
      template: `<div data-test="intel-map-props">{{ String(enableCompare) }}|{{ compareLeftTilesUrl || '' }}|{{ compareRightTilesUrl || '' }}</div>`,
    });

    const page = await import("../HistoricalComparisonPage.vue");
    const wrapper = mount(page.default, {
      global: {
        stubs: { IntelMap: IntelMapStub },
      },
    });

    await Promise.resolve();
    await Promise.resolve();
    const selects = wrapper.findAll("select");
    await selects[0].setValue(11 as any);
    await selects[1].setValue(12 as any);
    const loadBtn = wrapper.findAll("button").find((b) => b.text().includes("Load Split Tiles"));
    expect(loadBtn).toBeTruthy();
    await loadBtn!.trigger("click");
    await Promise.resolve();
    await Promise.resolve();

    const propsText = wrapper.get('[data-test="intel-map-props"]').text();
    expect(propsText).toContain("true");
    expect(propsText).toContain("http://tiles/before/{z}/{x}/{y}.png");
    expect(propsText).toContain("http://tiles/after/{z}/{x}/{y}.png");
  });
});
