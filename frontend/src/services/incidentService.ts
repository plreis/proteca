import {
  CreateIncidentDTO,
  Incident,
  IncidentActionLog,
  IncidentCategory,
  IncidentStatus,
} from '@/types';

import { apiRequest } from './api';

interface IncidentResponse {
  id: string;
  school_id: string;
  session_id: string;
  device_id?: string | null;
  category: IncidentCategory;
  description: string;
  status: IncidentStatus;
  created_at: string;
  updated_at?: string | null;
  closing_justification?: string | null;
  actions: IncidentActionLog[];
}

interface IncidentFilters {
  sessionId?: string;
  category?: IncidentCategory;
  status?: IncidentStatus;
}

function getToken(): string | undefined {
  return localStorage.getItem('proteca_token') ?? undefined;
}

function toIncident(data: IncidentResponse): Incident {
  return {
    id: data.id,
    schoolId: data.school_id,
    sessionId: data.session_id,
    deviceId: data.device_id ?? undefined,
    category: data.category,
    description: data.description,
    status: data.status,
    createdAt: data.created_at,
    updatedAt: data.updated_at ?? undefined,
    closingJustification: data.closing_justification ?? undefined,
    actions: data.actions,
  };
}

export const incidentService = {
  async getIncidents(
    filters?: IncidentFilters
  ): Promise<Incident[]> {
    const response = await apiRequest<IncidentResponse[]>(
      '/incidents',
      {
        method: 'GET',
        token: getToken(),
        query: {
          session_id: filters?.sessionId,
          category: filters?.category,
          incident_status: filters?.status,
        },
      }
    );

    return response.map(toIncident);
  },

  async getIncident(id: string): Promise<Incident> {
    const response = await apiRequest<IncidentResponse>(
      `/incidents/${id}`,
      {
        method: 'GET',
        token: getToken(),
      }
    );

    return toIncident(response);
  },

  async createIncident(
    dto: CreateIncidentDTO
  ): Promise<Incident> {
    const response = await apiRequest<IncidentResponse>(
      '/incidents',
      {
        method: 'POST',
        token: getToken(),
        body: {
          session_id: dto.sessionId,
          device_id: dto.deviceId,
          category: dto.category,
          description: dto.description,
        },
      }
    );

    return toIncident(response);
  },

  async updateIncidentStatus(
    id: string,
    status: IncidentStatus,
    justification?: string
  ): Promise<Incident> {
    const response = await apiRequest<IncidentResponse>(
      `/incidents/${id}/status`,
      {
        method: 'PATCH',
        token: getToken(),
        body: {
          status,
          justification,
        },
      }
    );

    return toIncident(response);
  },
};