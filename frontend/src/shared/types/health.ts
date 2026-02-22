export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  request_id: string;
  timestamp: string;
};
