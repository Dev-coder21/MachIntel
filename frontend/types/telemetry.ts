export interface TelemetryCycle {
  id: string;
  source_cycle: number;
  event_timestamp?: string | null;
  split_type: string;
  op_setting_1: number;
  op_setting_2: number;
  op_setting_3: number;
  sensor_1: number;
  sensor_2: number;
  sensor_3: number;
  sensor_4: number;
  sensor_5: number;
  sensor_6: number;
  sensor_7: number;
  sensor_8: number;
  sensor_9: number;
  sensor_10: number;
  sensor_11: number;
  sensor_12: number;
  sensor_13: number;
  sensor_14: number;
  sensor_15: number;
  sensor_16: number;
  sensor_17: number;
  sensor_18: number;
  sensor_19: number;
  sensor_20: number;
  sensor_21: number;
}

export interface TelemetryQueryResponse {
  machine_id: string;
  total_records: number;
  min_cycle: number;
  max_cycle: number;
  start_cycle: number;
  end_cycle: number;
  returned_records: number;
  records: TelemetryCycle[];
}
