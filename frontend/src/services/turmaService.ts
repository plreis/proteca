// frontend/src/services/turmaService.ts
// Tela da turma (ADR 0004). As consultas públicas não levam token, cookies nem
// referência da página: a tela da turma só lê o que o professor decidiu enviar.

import { ApiError, apiRequest, redirectToLoginAfterExpiredSession } from './api';
import type { ProtecaIntervention } from '@/types';
import type { ClassScreen, ClassScreenResponse, ClassVoice } from '@/types/turma';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '');

export const CLASS_CODE_LENGTH = 6;

/** Deixa o código em maiúsculas e só com letras e números (AULA8B). */
export function normalizeClassCode(value: string): string {
  return value
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, CLASS_CODE_LENGTH);
}

function toClassScreen(data: ClassScreenResponse): ClassScreen {
  return {
    classCode: data.class_code,
    objective: data.objective,
    sessionStatus: data.session_status,
    intervention: data.intervention ?? null,
    broadcastAt: data.broadcast_at ?? null,
    audioReady: Boolean(data.audio_ready),
  };
}

function publicUrl(path: string): string {
  if (!API_URL) {
    throw new Error('NEXT_PUBLIC_API_URL não está configurada.');
  }
  return `${API_URL}${path}`;
}

// Sem credenciais nem Referer; `no-store` evita mostrar uma intervenção antiga do cache.
const publicRequest: RequestInit = {
  method: 'GET',
  credentials: 'omit',
  cache: 'no-store',
  referrerPolicy: 'no-referrer',
};

/** `GET /turma/{codigo}`: lança ApiError 404 quando o código não existe. */
export async function fetchClassScreen(code: string, signal?: AbortSignal): Promise<ClassScreen> {
  const response = await fetch(publicUrl(`/turma/${encodeURIComponent(code)}`), {
    ...publicRequest,
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    throw new ApiError(`A API respondeu com o status ${response.status}.`, response.status);
  }

  return toClassScreen((await response.json()) as ClassScreenResponse);
}

/** `GET /turma/{codigo}/voz`: devolve null enquanto o áudio ainda não existe (404). */
export async function fetchClassVoice(code: string, signal?: AbortSignal): Promise<ClassVoice | null> {
  const response = await fetch(publicUrl(`/turma/${encodeURIComponent(code)}/voz`), {
    ...publicRequest,
    signal,
  });

  if (response.status === 404) return null;
  if (!response.ok) {
    throw new ApiError(`Voz indisponível (status ${response.status}).`, response.status);
  }

  const audio = await response.blob();
  return {
    audioUrl: URL.createObjectURL(audio),
    model: response.headers.get('X-Proteca-Voice-Model') ?? 'gemini-tts',
  };
}

async function teacherRequest<T>(path: string, init: { method: string; body?: unknown }): Promise<T> {
  try {
    return await apiRequest<T>(path, {
      ...init,
      token: localStorage.getItem('proteca_token') ?? undefined,
    });
  } catch (error) {
    // Token vencido: volta ao login com o aviso, como nas outras telas do professor.
    if (error instanceof ApiError && error.status === 401) {
      redirectToLoginAfterExpiredSession();
    }
    throw error;
  }
}

/** Professor: `POST /sessions/{id}/turma`. A API responde 409 se a sessão estiver encerrada. */
export async function showOnClassScreen(
  sessionId: string,
  intervention: ProtecaIntervention
): Promise<ClassScreen> {
  const data = await teacherRequest<ClassScreenResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/turma`,
    {
      method: 'POST',
      body: {
        intervention: {
          state: intervention.state,
          title: intervention.title,
          message: intervention.message,
          prompt: intervention.prompt,
          speech: intervention.speech ?? null,
        },
      },
    }
  );
  return toClassScreen(data);
}

/** Professor: `DELETE /sessions/{id}/turma` (204). A turma volta a ver o Proteca aguardando. */
export async function clearClassScreen(sessionId: string): Promise<void> {
  await teacherRequest<void>(`/sessions/${encodeURIComponent(sessionId)}/turma`, {
    method: 'DELETE',
  });
}
