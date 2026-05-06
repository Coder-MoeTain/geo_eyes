import { createRouter, createWebHistory } from "vue-router";
import { useIntelStore } from "./stores/intel";
import LoginPage from "./views/LoginPage.vue";
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
  { path: "/", component: LoginPage },
  { path: "/dashboard", component: DashboardPage, meta: { requiresAuth: true } },
  { path: "/detections", component: DetectionPage, meta: { requiresAuth: true } },
  { path: "/models", component: ModelManagerPage, meta: { requiresAuth: true, adminOnly: true } },
  { path: "/imagery", component: ImageryViewerPage, meta: { requiresAuth: true } },
  { path: "/historical", component: HistoricalComparisonPage, meta: { requiresAuth: true } },
  { path: "/alerts", component: AlertCenterPage, meta: { requiresAuth: true } },
  { path: "/admin", component: AdminPanelPage, meta: { requiresAuth: true, adminOnly: true } },
  { path: "/upload-detect", component: UploadDetectPage, meta: { requiresAuth: true } },
  { path: "/training", component: TrainingOpsPage, meta: { requiresAuth: true, adminOnly: true } },
  { path: "/airports", component: AirportIntelligencePage, meta: { requiresAuth: true } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const store = useIntelStore();
  if (to.meta.requiresAuth && !store.token) return "/";
  if (to.meta.adminOnly && store.role !== "admin") return "/dashboard";
  return true;
});

export default router;
