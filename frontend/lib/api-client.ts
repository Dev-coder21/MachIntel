import { AuthResponse, LoginCredentials, User } from "@/types/auth";
import { FoundationStats, Machine, MachineDetail, MachineListResponse } from "@/types/machine";
import { TelemetryQueryResponse } from "@/types/telemetry";
import { DatasetMetadata, DatasetListResponse } from "@/types/dataset";
import {
  CorrelationMatrixResponse,
  FeaturePreviewResponse,
  FleetAnalyticsOverviewResponse,
  MachineAnalyticsSummary,
  MachineComparisonResponse,
  SensorSummaryItem,
  SensorTrendResponse,
} from "@/types/analytics";
import {
  ModelEvaluationItem,
  ModelGateReport,
  ModelIntegrityReport,
  ModelMonitoringSummary,
  ModelPromotionItem,
  ModelRegistryItem,
  ModelRegistryListResponse,
} from "@/types/model";
import {
  FleetPrognosticsOverview,
  PredictionCreateRequest,
  PredictionItem,
  PredictionListResponse,
} from "@/types/prediction";
import { RiskAssessmentItem, RiskTransitionItem } from "@/types/risk";
import { AlertItem, AlertListResponse, AlertSummary } from "@/types/alert";
import {
  InspectionResult,
  InspectionRun,
  InspectionRunSummary,
} from "@/types/inspection";
import {
  ConfusionMatrixAnalytics,
  DefectClassAnalytics,
  InspectionRunAnalyticsSummary,
  InspectionRunProvenance,
  LocalizationAnalytics,
  RunComparison,
  ScoreDistribution,
} from "@/types/inspection-analytics";
import {
  EvidenceBundle,
  EvidenceProvenance,
  EvidenceRecord,
  EvidenceRelationship,
  EvidenceSearchResponse,
  EvidenceTimelineItem,
} from "@/types/evidence";
import {
  CreateWorkOrderPayload,
  MaintenanceSummary,
  MaintenanceWorkOrder,
  MaintenanceWorkOrderDetail,
} from "@/types/maintenance";
import {
  AIInvestigationResponse,
  AIInvestigationSummary,
  InvestigationContext,
  ToolDefinitionSchema,
} from "@/types/ai-inspector";
import { Job, JobListResponse, JobSummary, WorkerHealth } from "@/types/job";


const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiClientError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(message: string, code: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("machintel_token");
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem("machintel_token", token);
      } else {
        localStorage.removeItem("machintel_token");
      }
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== "undefined") {
      this.token = localStorage.getItem("machintel_token");
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.setToken(null);
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login?session_expired=true";
      }
    }

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        throw new ApiClientError(
          response.statusText || "HTTP Request Failed",
          "HTTP_ERROR",
          response.status
        );
      }

      const err = errorData?.error;
      throw new ApiClientError(
        err?.message || "An unexpected API error occurred",
        err?.code || "API_ERROR",
        response.status,
        err?.details
      );
    }

    return response.json() as Promise<T>;
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  // Auth Specific Helpers
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const res = await this.post<AuthResponse>("/auth/login", credentials);
    if (res.access_token) {
      this.setToken(res.access_token);
    }
    return res;
  }

  async getMe(): Promise<User> {
    return this.get<User>("/auth/me");
  }

  async logout(): Promise<void> {
    this.setToken(null);
  }

  // System Health Helpers
  async getHealth(): Promise<{ status: string; version: string; environment: string }> {
    return this.get("/health");
  }

  async getDbHealth(): Promise<{ status: string; database: string; latency_ms: number }> {
    return this.get("/health/db");
  }

  // Machines
  async getFoundationStats(): Promise<FoundationStats> {
    return this.get<FoundationStats>("/machines/stats/summary");
  }

  async getMachines(params?: {
    skip?: number;
    limit?: number;
    machine_type?: string;
    status?: string;
    split_category?: string;
    search?: string;
  }): Promise<MachineListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.skip !== undefined) searchParams.set("skip", params.skip.toString());
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    if (params?.machine_type) searchParams.set("machine_type", params.machine_type);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.split_category) searchParams.set("split_category", params.split_category);
    if (params?.search) searchParams.set("search", params.search);

    const query = searchParams.toString();
    return this.get<MachineListResponse>(`/machines${query ? `?${query}` : ""}`);
  }

  async getMachine(machineId: string): Promise<MachineDetail> {
    return this.get<MachineDetail>(`/machines/${machineId}`);
  }

  async getMachineTelemetry(
    machineId: string,
    params?: {
      start_cycle?: number;
      end_cycle?: number;
      limit?: number;
      offset?: number;
    }
  ): Promise<TelemetryQueryResponse> {
    const searchParams = new URLSearchParams();
    if (params?.start_cycle !== undefined) searchParams.set("start_cycle", params.start_cycle.toString());
    if (params?.end_cycle !== undefined) searchParams.set("end_cycle", params.end_cycle.toString());
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    if (params?.offset !== undefined) searchParams.set("offset", params.offset.toString());

    const query = searchParams.toString();
    return this.get<TelemetryQueryResponse>(`/machines/${machineId}/telemetry${query ? `?${query}` : ""}`);
  }

  // Datasets
  async getDatasets(skip: number = 0, limit: number = 20): Promise<DatasetListResponse> {
    return this.get<DatasetListResponse>(`/datasets?skip=${skip}&limit=${limit}`);
  }

  async getDataset(datasetId: string): Promise<DatasetMetadata> {
    return this.get<DatasetMetadata>(`/datasets/${datasetId}`);
  }

  // Machine Analytics
  async getMachineAnalyticsSummary(machineId: string): Promise<MachineAnalyticsSummary> {
    return this.get<MachineAnalyticsSummary>(`/machines/${machineId}/analytics/summary`);
  }

  async getMachineSensorAnalytics(machineId: string): Promise<SensorSummaryItem[]> {
    return this.get<SensorSummaryItem[]>(`/machines/${machineId}/analytics/sensors`);
  }

  async getMachineSensorTrends(
    machineId: string,
    sensor: string,
    params?: { window?: number; max_points?: number }
  ): Promise<SensorTrendResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set("sensor", sensor);
    if (params?.window) searchParams.set("window", params.window.toString());
    if (params?.max_points) searchParams.set("max_points", params.max_points.toString());
    return this.get<SensorTrendResponse>(`/machines/${machineId}/analytics/trends?${searchParams.toString()}`);
  }

  async getMachineCorrelation(machineId: string, channels?: string[]): Promise<CorrelationMatrixResponse> {
    const searchParams = new URLSearchParams();
    if (channels && channels.length > 0) {
      channels.forEach((c) => searchParams.append("channels", c));
    }
    const query = searchParams.toString();
    return this.get<CorrelationMatrixResponse>(`/machines/${machineId}/analytics/correlation${query ? `?${query}` : ""}`);
  }

  async getMachineFeaturePreview(
    machineId: string,
    params?: { start_cycle?: number; end_cycle?: number; window?: number }
  ): Promise<FeaturePreviewResponse> {
    const searchParams = new URLSearchParams();
    if (params?.start_cycle) searchParams.set("start_cycle", params.start_cycle.toString());
    if (params?.end_cycle) searchParams.set("end_cycle", params.end_cycle.toString());
    if (params?.window) searchParams.set("window", params.window.toString());
    const query = searchParams.toString();
    return this.get<FeaturePreviewResponse>(`/machines/${machineId}/analytics/features${query ? `?${query}` : ""}`);
  }

  async getFleetAnalyticsOverview(): Promise<FleetAnalyticsOverviewResponse> {
    return this.get<FleetAnalyticsOverviewResponse>("/machines/analytics/overview");
  }

  async compareMachines(machineIds: string[]): Promise<MachineComparisonResponse> {
    return this.get<MachineComparisonResponse>(`/machines/analytics/compare?machine_ids=${encodeURIComponent(machineIds.join(","))}`);
  }

  // Model Registry & ML Lifecycle
  async getModels(params?: {
    domain?: string;
    model_family?: string;
    status?: string;
    version?: string;
  }): Promise<ModelRegistryListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.domain) searchParams.set("domain", params.domain);
    if (params?.model_family) searchParams.set("model_family", params.model_family);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.version) searchParams.set("version", params.version);
    const query = searchParams.toString();
    return this.get<ModelRegistryListResponse>(`/models${query ? `?${query}` : ""}`);
  }

  async getModel(modelId: string): Promise<ModelRegistryItem> {
    return this.get<ModelRegistryItem>(`/models/${modelId}`);
  }

  async getModelIntegrity(modelId: string): Promise<ModelIntegrityReport> {
    return this.get<ModelIntegrityReport>(`/models/${modelId}/integrity`);
  }

  async verifyModelIntegrity(modelId: string): Promise<ModelIntegrityReport> {
    return this.post<ModelIntegrityReport>(`/models/${modelId}/verify-integrity`, {});
  }

  async getModelGates(modelId: string): Promise<ModelGateReport> {
    return this.get<ModelGateReport>(`/models/${modelId}/gates`);
  }

  async getModelEvaluations(modelId: string): Promise<ModelEvaluationItem[]> {
    return this.get<ModelEvaluationItem[]>(`/models/${modelId}/evaluations`);
  }

  async getModelPromotions(modelId: string): Promise<ModelPromotionItem[]> {
    return this.get<ModelPromotionItem[]>(`/models/${modelId}/promotions`);
  }

  async promoteModel(modelId: string, reason: string): Promise<ModelRegistryItem> {
    return this.post<ModelRegistryItem>(`/models/${modelId}/promote`, { reason });
  }

  async retireModel(modelId: string, reason: string): Promise<ModelRegistryItem> {
    return this.post<ModelRegistryItem>(`/models/${modelId}/retire`, { reason });
  }

  async getModelMonitoringSummary(domain: string = "MACHINE_HEALTH"): Promise<ModelMonitoringSummary> {
    return this.get<ModelMonitoringSummary>(`/models/monitoring/summary?domain=${encodeURIComponent(domain)}`);
  }

  // Prognostics & Predictions
  async getFleetPrognosticsOverview(): Promise<FleetPrognosticsOverview> {
    return this.get<FleetPrognosticsOverview>("/predictions/fleet/overview");
  }

  async getMachineLatestPrediction(machineId: string): Promise<PredictionItem | null> {
    return this.get<PredictionItem | null>(`/machines/${machineId}/predictions/latest`);
  }

  async getMachinePredictionHistory(
    machineId: string,
    page: number = 1,
    pageSize: number = 50
  ): Promise<PredictionListResponse> {
    return this.get<PredictionListResponse>(
      `/machines/${machineId}/predictions?page=${page}&page_size=${pageSize}`
    );
  }

  async createMachinePrediction(
    machineId: string,
    payload?: PredictionCreateRequest
  ): Promise<PredictionItem> {
    return this.post<PredictionItem>(`/machines/${machineId}/predictions`, payload || {});
  }

  // Risk Intelligence
  async getMachineLatestRisk(machineId: string): Promise<RiskAssessmentItem | null> {
    return this.get<RiskAssessmentItem | null>(`/machines/${machineId}/risk/latest`);
  }

  async getMachineRiskHistory(
    machineId: string,
    skip: number = 0,
    limit: number = 50
  ): Promise<RiskAssessmentItem[]> {
    return this.get<RiskAssessmentItem[]>(
      `/machines/${machineId}/risk/history?skip=${skip}&limit=${limit}`
    );
  }

  async evaluateMachineRisk(
    machineId: string,
    predictionId?: string
  ): Promise<RiskAssessmentItem> {
    return this.post<RiskAssessmentItem>(
      `/machines/${machineId}/risk/evaluate`,
      predictionId ? { prediction_id: predictionId } : {}
    );
  }

  // Alerts Console
  async getAlerts(params?: {
    status?: string;
    severity?: string;
    machine_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<AlertListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.severity) searchParams.set("severity", params.severity);
    if (params?.machine_id) searchParams.set("machine_id", params.machine_id);
    if (params?.skip !== undefined) searchParams.set("skip", params.skip.toString());
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    const query = searchParams.toString();
    return this.get<AlertListResponse>(`/alerts${query ? `?${query}` : ""}`);
  }

  async getAlertSummary(): Promise<AlertSummary> {
    return this.get<AlertSummary>("/alerts/summary");
  }

  async getAlert(alertId: string): Promise<AlertItem> {
    return this.get<AlertItem>(`/alerts/${alertId}`);
  }

  async acknowledgeAlert(alertId: string, note?: string): Promise<AlertItem> {
    return this.post<AlertItem>(`/alerts/${alertId}/acknowledge`, note ? { note } : {});
  }

  async resolveAlert(alertId: string, note?: string): Promise<AlertItem> {
    return this.post<AlertItem>(`/alerts/${alertId}/resolve`, note ? { note } : {});
  }

  // Visual Inspection (Computer Vision)
  async getInspectionRuns(params?: {
    category?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<InspectionRun[]> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set("category", params.category);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    if (params?.offset !== undefined) searchParams.set("offset", params.offset.toString());
    const query = searchParams.toString();
    return this.get<InspectionRun[]>(`/inspections${query ? `?${query}` : ""}`);
  }

  async getInspectionRun(id: string): Promise<InspectionRun> {
    return this.get<InspectionRun>(`/inspections/${id}`);
  }

  async getInspectionSummary(id: string): Promise<InspectionRunSummary> {
    return this.get<InspectionRunSummary>(`/inspections/${id}/summary`);
  }

  async getInspectionResults(
    id: string,
    params?: {
      defect_class?: string;
      decision?: string;
      limit?: number;
      offset?: number;
    }
  ): Promise<InspectionResult[]> {
    const searchParams = new URLSearchParams();
    if (params?.defect_class) searchParams.set("defect_class", params.defect_class);
    if (params?.decision) searchParams.set("decision", params.decision);
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    if (params?.offset !== undefined) searchParams.set("offset", params.offset.toString());
    const query = searchParams.toString();
    return this.get<InspectionResult[]>(`/inspections/${id}/results${query ? `?${query}` : ""}`);
  }

  async getInspectionResult(resultId: string): Promise<InspectionResult> {
    return this.get<InspectionResult>(`/inspections/results/${resultId}`);
  }

  async triggerInspectionRun(category: string = "metal_nut"): Promise<InspectionRun> {
    return this.post<InspectionRun>("/inspections/run", { category });
  }

  getInspectionArtifactUrl(resultId: string, type: "heatmap" | "overlay" | "original" | "mask"): string {
    const token = this.token || (typeof window !== "undefined" ? localStorage.getItem("machintel_token") : null);
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
    return `${API_BASE_URL}/inspections/results/${resultId}/${type}${tokenParam}`;
  }

  // Inspection Analytics (Milestone M7)
  async getInspectionAnalyticsRuns(params?: {
    dataset_identifier?: string;
    model_version?: string;
    policy_version?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<InspectionRun[]> {
    const searchParams = new URLSearchParams();
    if (params?.dataset_identifier) searchParams.set("dataset_identifier", params.dataset_identifier);
    if (params?.model_version) searchParams.set("model_version", params.model_version);
    if (params?.policy_version) searchParams.set("policy_version", params.policy_version);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    if (params?.offset !== undefined) searchParams.set("offset", params.offset.toString());
    const query = searchParams.toString();
    return this.get<InspectionRun[]>(`/inspection-analytics/runs${query ? `?${query}` : ""}`);
  }

  async getInspectionAnalyticsSummary(runId: string): Promise<InspectionRunAnalyticsSummary> {
    return this.get<InspectionRunAnalyticsSummary>(`/inspection-analytics/runs/${runId}/summary`);
  }

  async getInspectionAnalyticsScores(runId: string, bins?: number): Promise<ScoreDistribution> {
    const query = bins ? `?bins=${bins}` : "";
    return this.get<ScoreDistribution>(`/inspection-analytics/runs/${runId}/scores${query}`);
  }

  async getInspectionAnalyticsDefects(runId: string): Promise<DefectClassAnalytics> {
    return this.get<DefectClassAnalytics>(`/inspection-analytics/runs/${runId}/defects`);
  }

  async getInspectionAnalyticsConfusionMatrix(runId: string): Promise<ConfusionMatrixAnalytics> {
    return this.get<ConfusionMatrixAnalytics>(`/inspection-analytics/runs/${runId}/confusion-matrix`);
  }

  async getInspectionAnalyticsLocalization(runId: string): Promise<LocalizationAnalytics> {
    return this.get<LocalizationAnalytics>(`/inspection-analytics/runs/${runId}/localization`);
  }

  async getInspectionAnalyticsProvenance(runId: string): Promise<InspectionRunProvenance> {
    return this.get<InspectionRunProvenance>(`/inspection-analytics/runs/${runId}/provenance`);
  }

  async getInspectionAnalyticsComparison(): Promise<RunComparison> {
    return this.get<RunComparison>("/inspection-analytics/compare");
  }

  // Evidence Intelligence (Milestone M8)
  async searchEvidence(params?: {
    domain?: string;
    entity_type?: string;
    entity_id?: string;
    evidence_type?: string;
    quality_state?: string;
    source?: string;
    model_version?: string;
    policy_version?: string;
    observation_cycle?: number;
    limit?: number;
    offset?: number;
  }): Promise<EvidenceSearchResponse> {
    const searchParams = new URLSearchParams();
    if (params?.domain) searchParams.set("domain", params.domain);
    if (params?.entity_type) searchParams.set("entity_type", params.entity_type);
    if (params?.entity_id) searchParams.set("entity_id", params.entity_id);
    if (params?.evidence_type) searchParams.set("evidence_type", params.evidence_type);
    if (params?.quality_state) searchParams.set("quality_state", params.quality_state);
    if (params?.source) searchParams.set("source", params.source);
    if (params?.model_version) searchParams.set("model_version", params.model_version);
    if (params?.policy_version) searchParams.set("policy_version", params.policy_version);
    if (params?.observation_cycle !== undefined) searchParams.set("observation_cycle", params.observation_cycle.toString());
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    if (params?.offset !== undefined) searchParams.set("offset", params.offset.toString());
    const query = searchParams.toString();
    return this.get<EvidenceSearchResponse>(`/evidence${query ? `?${query}` : ""}`);
  }

  async getEvidenceRecord(evidenceId: string): Promise<EvidenceRecord> {
    return this.get<EvidenceRecord>(`/evidence/${evidenceId}`);
  }

  async getEntityEvidence(
    entityType: string,
    entityId: string,
    domain?: string
  ): Promise<EvidenceRecord[]> {
    const query = domain ? `?domain=${encodeURIComponent(domain)}` : "";
    return this.get<EvidenceRecord[]>(`/evidence/entity/${entityType}/${entityId}${query}`);
  }

  async getEntityEvidenceTimeline(
    entityType: string,
    entityId: string
  ): Promise<EvidenceTimelineItem[]> {
    return this.get<EvidenceTimelineItem[]>(`/evidence/entity/${entityType}/${entityId}/timeline`);
  }

  async getEvidenceBundles(params?: {
    domain?: string;
    entity_type?: string;
    entity_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<EvidenceBundle[]> {
    const searchParams = new URLSearchParams();
    if (params?.domain) searchParams.set("domain", params.domain);
    if (params?.entity_type) searchParams.set("entity_type", params.entity_type);
    if (params?.entity_id) searchParams.set("entity_id", params.entity_id);
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    if (params?.offset !== undefined) searchParams.set("offset", params.offset.toString());
    const query = searchParams.toString();
    return this.get<EvidenceBundle[]>(`/evidence/bundles${query ? `?${query}` : ""}`);
  }

  async getEvidenceBundle(bundleId: string): Promise<EvidenceBundle> {
    return this.get<EvidenceBundle>(`/evidence/bundles/${bundleId}`);
  }

  async getEvidenceBundleTimeline(bundleId: string): Promise<EvidenceTimelineItem[]> {
    return this.get<EvidenceTimelineItem[]>(`/evidence/bundles/${bundleId}/timeline`);
  }

  async getEvidenceRelationships(
    evidenceId: string
  ): Promise<{ outgoing: EvidenceRelationship[]; incoming: EvidenceRelationship[] }> {
    return this.get<{ outgoing: EvidenceRelationship[]; incoming: EvidenceRelationship[] }>(
      `/evidence/relationships/${evidenceId}`
    );
  }

  async getEvidenceProvenance(evidenceId: string): Promise<EvidenceProvenance> {
    return this.get<EvidenceProvenance>(`/evidence/provenance/${evidenceId}`);
  }

  // --- Maintenance Operations (M9) ---

  async getMaintenanceSummary(): Promise<MaintenanceSummary> {
    return this.get<MaintenanceSummary>("/maintenance/summary");
  }

  async listWorkOrders(params?: {
    status?: string;
    priority?: string;
    source_domain?: string;
    machine_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<MaintenanceWorkOrder[]> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.priority) searchParams.set("priority", params.priority);
    if (params?.source_domain) searchParams.set("source_domain", params.source_domain);
    if (params?.machine_id) searchParams.set("machine_id", params.machine_id);
    if (params?.skip !== undefined) searchParams.set("skip", params.skip.toString());
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    const query = searchParams.toString();
    return this.get<MaintenanceWorkOrder[]>(`/maintenance/work-orders${query ? `?${query}` : ""}`);
  }

  async getWorkOrderDetail(id: string): Promise<MaintenanceWorkOrderDetail> {
    return this.get<MaintenanceWorkOrderDetail>(`/maintenance/work-orders/${id}`);
  }

  async createWorkOrder(payload: CreateWorkOrderPayload): Promise<MaintenanceWorkOrder> {
    return this.post<MaintenanceWorkOrder>("/maintenance/work-orders", payload);
  }

  async draftRecommendationFromRisk(riskId: string): Promise<MaintenanceWorkOrder> {
    return this.post<MaintenanceWorkOrder>(`/maintenance/recommendations/from-risk/${riskId}`);
  }

  async draftRecommendationFromInspection(inspectionResultId: string): Promise<MaintenanceWorkOrder> {
    return this.post<MaintenanceWorkOrder>(`/maintenance/recommendations/from-inspection/${inspectionResultId}`);
  }

  async acknowledgeWorkOrder(
    id: string,
    notes?: string,
    assignedToId?: string
  ): Promise<MaintenanceWorkOrder> {
    return this.post<MaintenanceWorkOrder>(`/maintenance/work-orders/${id}/acknowledge`, {
      notes,
      assigned_to_id: assignedToId,
    });
  }

  async startWorkOrder(id: string, notes?: string): Promise<MaintenanceWorkOrder> {
    return this.post<MaintenanceWorkOrder>(`/maintenance/work-orders/${id}/start`, { notes });
  }

  async completeWorkOrder(
    id: string,
    resolutionNotes: string,
    notes?: string
  ): Promise<MaintenanceWorkOrder> {
    return this.post<MaintenanceWorkOrder>(`/maintenance/work-orders/${id}/complete`, {
      resolution_notes: resolutionNotes,
      notes,
    });
  }

  async cancelWorkOrder(id: string, reason: string, notes?: string): Promise<MaintenanceWorkOrder> {
    return this.post<MaintenanceWorkOrder>(`/maintenance/work-orders/${id}/cancel`, {
      reason,
      notes,
    });
  }

  // AI Inspector (Milestone M10)
  async createInvestigation(question: string, context?: InvestigationContext): Promise<AIInvestigationResponse> {
    return this.post<AIInvestigationResponse>("/ai-inspector/investigations", {
      question,
      context,
    });
  }

  async listInvestigations(params?: { limit?: number; offset?: number; status?: string }): Promise<AIInvestigationSummary[]> {
    const searchParams = new URLSearchParams();
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    if (params?.offset !== undefined) searchParams.set("offset", params.offset.toString());
    if (params?.status) searchParams.set("status", params.status);
    const query = searchParams.toString();
    return this.get<AIInvestigationSummary[]>(`/ai-inspector/investigations${query ? `?${query}` : ""}`);
  }

  async getInvestigation(id: string): Promise<AIInvestigationResponse> {
    return this.get<AIInvestigationResponse>(`/ai-inspector/investigations/${id}`);
  }

  async getInspectorTools(): Promise<ToolDefinitionSchema[]> {
    return this.get<ToolDefinitionSchema[]>("/ai-inspector/tools");
  }

  // Background Jobs & Operational Infrastructure (Milestone M12)
  async getJobs(params?: { status?: string; job_type?: string; skip?: number; limit?: number }): Promise<JobListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.job_type) searchParams.set("job_type", params.job_type);
    if (params?.skip !== undefined) searchParams.set("skip", params.skip.toString());
    if (params?.limit !== undefined) searchParams.set("limit", params.limit.toString());
    const query = searchParams.toString();
    return this.get<JobListResponse>(`/jobs${query ? `?${query}` : ""}`);
  }

  async getJobDetail(id: string): Promise<Job> {
    return this.get<Job>(`/jobs/${id}`);
  }

  async getJobSummary(): Promise<JobSummary> {
    return this.get<JobSummary>("/jobs/summary");
  }

  async getWorkerHealth(): Promise<WorkerHealth> {
    return this.get<WorkerHealth>("/jobs/health");
  }

  async triggerJob(jobType: string, payload?: Record<string, any>): Promise<Job> {
    return this.post<Job>(`/jobs/${jobType}`, { payload: payload || {} });
  }
}

export const apiClient = new ApiClient();

