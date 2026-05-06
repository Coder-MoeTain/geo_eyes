import { defineStore } from "pinia";
import { apiClient as api } from "../services/api";

export const useIntelStore = defineStore("intel", {
  state: () => ({
    token: "",
    role: "user",
    taskId: "",
    taskResult: null as any,
    detections: [] as any[],
    stats: null as any,
    heatmap: null as any,
    models: [] as any[],
    trainingOptions: null as any,
    airports: [] as any[],
    uploadedTileUrl: "",
    latestUpload: null as any,
  }),
  actions: {
    authHeaders() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {};
    },
    async login(username: string, password: string) {
      const { data } = await api.post("/api/v1/login", { username, password });
      this.token = data.access_token;
      const me = await api.get("/api/v1/auth/me", { headers: this.authHeaders() });
      this.role = me.data.role || "user";
    },
    async triggerDetection(payload: {
      latitude?: number;
      longitude?: number;
      lat?: number;
      lon?: number;
      provider: string;
      cloud_max?: number;
      start_date?: string | null;
      end_date?: string | null;
      model_id?: number | null;
      aoi_geojson?: any;
    }) {
      const { data } = await api.post("/api/v1/detect/coordinate", {
        latitude: payload.latitude ?? payload.lat,
        longitude: payload.longitude ?? payload.lon,
        provider: payload.provider,
        cloud_max: payload.cloud_max,
        start_date: payload.start_date,
        end_date: payload.end_date,
        model_id: payload.model_id,
        aoi_geojson: payload.aoi_geojson,
      }, { headers: this.authHeaders() });
      this.taskId = data.task_id;
    },
    async uploadImage(file: File) {
      const sign = await api.post("/api/v1/uploads/sign", {
        filename: file.name,
        mime_type: file.type || undefined,
        size_bytes: file.size,
      }, { headers: this.authHeaders() });
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post(sign.data.upload_url, fd, {
        headers: { ...this.authHeaders(), "Content-Type": "multipart/form-data" },
      });
      this.latestUpload = data;
      return data as { image_id: number };
    },
    async pollTask() {
      if (!this.taskId) return;
      const { data } = await api.get(`/api/v1/jobs/${this.taskId}`, { headers: this.authHeaders() });
      this.taskResult = data;
      if (data?.result?.detections) this.detections = data.result.detections;
    },
    async cancelTask() {
      if (!this.taskId) return;
      await api.post(`/api/v1/jobs/${this.taskId}/cancel`, {}, { headers: this.authHeaders() });
      this.taskResult = { ...(this.taskResult || {}), status: "cancelled", progress: 0 };
    },
    async loadDetections() {
      const { data } = await api.get("/api/v1/detections", { headers: this.authHeaders() });
      this.detections = data.items;
    },
    async loadStats() {
      const { data } = await api.get("/api/v1/aircraft-statistics", { headers: this.authHeaders() });
      this.stats = data;
    },
    async loadHeatmap(start_date?: string, end_date?: string) {
      const { data } = await api.get("/api/v1/heatmap", {
        headers: this.authHeaders(),
        params: { start_date, end_date },
      });
      this.heatmap = data;
    },
    async loadModels() {
      const { data } = await api.get("/api/v1/models", { headers: this.authHeaders() });
      this.models = data.items || [];
    },
    async loadTrainingOptions() {
      const { data } = await api.get("/api/v1/training/options", { headers: this.authHeaders() });
      this.trainingOptions = data;
      return data;
    },
    async activateModel(modelId: number) {
      await api.post(`/api/v1/models/${modelId}/activate`, {}, { headers: this.authHeaders() });
      await this.loadModels();
    },
    async disableModel(modelId: number) {
      await api.post(`/api/v1/models/${modelId}/disable`, {}, { headers: this.authHeaders() });
      await this.loadModels();
    },
    async deleteModel(modelId: number) {
      await api.delete(`/api/v1/models/${modelId}`, { headers: this.authHeaders() });
      await this.loadModels();
    },
    async uploadModel(file: File) {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/api/v1/models/upload", fd, {
        headers: { ...this.authHeaders(), "Content-Type": "multipart/form-data" },
      });
      await this.loadModels();
      return data;
    },
    async uploadAndDetect(file: File) {
      const uploaded = await this.uploadImage(file);
      const { data } = await api.post(`/api/v1/uploads/${uploaded.image_id}/detect`, {}, { headers: this.authHeaders() });
      this.taskId = data.task_id;
      return { ...data, image_id: uploaded.image_id };
    },
    async loadNearbyAirports(latitude: number, longitude: number, radius_km = 50) {
      const { data } = await api.get("/api/v1/airports/nearby", {
        headers: this.authHeaders(),
        params: { lat: latitude, lon: longitude, radius_m: radius_km * 1000 },
      });
      this.airports = data.items || [];
    },
    async loadUploadedTileUrl(imageId: number) {
      const { data } = await api.get(`/api/v1/uploaded-image/${imageId}/tiles`, { headers: this.authHeaders() });
      this.uploadedTileUrl = data.tiles_url;
      return data.tiles_url as string;
    },
    async rotateApiToken() {
      const { data } = await api.post("/api/v1/auth/api-token", {}, { headers: this.authHeaders() });
      return data.api_token as string;
    },
    async loadAudit(limit = 100) {
      const { data } = await api.get("/api/v1/admin/audit", {
        params: { limit },
        headers: this.authHeaders(),
      });
      return data;
    },
    async loadDetectionsGeojson(limit = 1000) {
      const { data } = await api.get("/api/v1/detections/geojson", {
        headers: this.authHeaders(),
        params: { limit },
      });
      return data;
    },
    async trainModel(payload: {
      training_method?: string;
      dataset_yaml: string;
      epochs: number;
      img_size: number;
      batch_size: number;
      model: string;
      device: string;
    }) {
      const { data } = await api.post("/api/v1/train-model", payload, { headers: this.authHeaders() });
      this.taskId = data.task_id;
      return data;
    },
  },
});
