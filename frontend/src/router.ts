import { createRouter, createWebHistory } from "vue-router";
import { useIntelStore } from "./stores/intel";
import LoginPage from "./views/LoginPage.vue";
import AppShell from "./layouts/AppShell.vue";
import DashboardPage from "./views/DashboardPage.vue";
import DetectionPage from "./views/DetectionPage.vue";
import ModelManagerPage from "./views/ModelManagerPage.vue";
import ImageryViewerPage from "./views/ImageryViewerPage.vue";
import HistoricalComparisonPage from "./views/HistoricalComparisonPage.vue";
import AlertCenterPage from "./views/AlertCenterPage.vue";
import AdminPanelPage from "./views/AdminPanelPage.vue";
import UploadDetectPage from "./views/UploadDetectPage.vue";
import TrainingOpsPage from "./views/TrainingOpsPage.vue";
import AirportIntelligencePage from "./views/AirportIntelligencePage.vue";

const routes = [
  { path: "/login", component: LoginPage, meta: { guestOnly: true, title: "Secure Access" } },
  {
    path: "/",
    component: AppShell,
    meta: { requiresAuth: true },
    children: [
      { path: "", redirect: "/dashboard" },
      { path: "dashboard", component: DashboardPage, meta: { title: "Dashboard" } },
      { path: "detections", component: DetectionPage, meta: { title: "Detections" } },
      { path: "models", component: ModelManagerPage, meta: { adminOnly: true, title: "Models" } },
      { path: "imagery", component: ImageryViewerPage, meta: { title: "Imagery" } },
      { path: "historical", component: HistoricalComparisonPage, meta: { title: "Historical" } },
      { path: "alerts", component: AlertCenterPage, meta: { title: "Alerts" } },
      { path: "admin", component: AdminPanelPage, meta: { adminOnly: true, title: "Admin" } },
      { path: "upload-detect", component: UploadDetectPage, meta: { title: "Upload/Detect" } },
      { path: "training", component: TrainingOpsPage, meta: { adminOnly: true, title: "Training" } },
      { path: "airports", component: AirportIntelligencePage, meta: { title: "Airports" } },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const store = useIntelStore();
  if (to.meta.requiresAuth && !store.token) return "/login";
  if (to.meta.guestOnly && store.token) return "/dashboard";
  if (to.meta.adminOnly && store.role !== "admin") return "/dashboard";
  return true;
});

export default router;
