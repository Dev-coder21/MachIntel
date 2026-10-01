export interface DatasetMetadata {
  id: string;
  dataset_name: string;
  dataset_identifier: string;
  source: string;
  source_url: string;
  license: string;
  retrieval_date: string;
  file_checksums: Record<string, { size_bytes: number; sha256: string }>;
  schema_version: string;
  preprocessing_version: string;
  ingestion_version: string;
  active_sensors: string[];
  invariant_sensors: string[];
  created_at: string;
  updated_at: string;
}

export interface DatasetListResponse {
  items: DatasetMetadata[];
  total: number;
}
