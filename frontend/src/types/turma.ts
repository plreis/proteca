// src/types/turma.ts
// Tipos da tela da turma (ADR 0004): só o objetivo da aula e a intervenção que o professor enviou.

import type { ProtecaIntervention, SessionStatus } from './index';

/**
 * Humor do Proteca como a interface mostra. A API manda `alerta` para o guardião
 * (o valor não muda no contrato); "neutro" é o mascote aguardando o professor.
 */
export type ProtecaHumor = 'acolhimento' | 'curiosidade' | 'guardiao';

export type MascotHumor = ProtecaHumor | 'neutro';

/** Resposta de `GET /turma/{codigo}` e de `POST /sessions/{id}/turma`. */
export interface ClassScreenResponse {
  class_code: string;
  objective: string;
  session_status: SessionStatus;
  intervention: ProtecaIntervention | null;
  broadcast_at: string | null;
  audio_ready: boolean;
}

export interface ClassScreen {
  classCode: string;
  objective: string;
  sessionStatus: SessionStatus;
  intervention: ProtecaIntervention | null;
  /** Momento em que o professor enviou a intervenção; muda a cada envio. */
  broadcastAt: string | null;
  /** A voz do Proteca desta intervenção já pode ser baixada em `/turma/{codigo}/voz`. */
  audioReady: boolean;
}

export interface ClassVoice {
  audioUrl: string;
  model: string;
}
