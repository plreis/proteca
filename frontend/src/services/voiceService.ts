// frontend/src/services/voiceService.ts

import { redirectToLoginAfterExpiredSession } from './api';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '');

export interface ProtecaVoice {
  audioUrl: string;
  model: string;
}

/**
 * Pede à API o áudio da intervenção. A API alterna entre os modelos TTS do Gemini
 * e responde 503 quando nenhum está disponível; nesse caso esta função lança erro.
 */
export async function requestProtecaVoice(text: string): Promise<ProtecaVoice> {
  if (!API_URL) {
    throw new Error('NEXT_PUBLIC_API_URL não está configurada.');
  }

  const response = await fetch(`${API_URL}/ia/voz`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('proteca_token') ?? ''}`,
    },
    body: JSON.stringify({ text }),
  });

  if (response.status === 401) {
    redirectToLoginAfterExpiredSession();
  }
  if (!response.ok) {
    throw new Error(`Voz indisponível (status ${response.status}).`);
  }

  const audio = await response.blob();
  return {
    audioUrl: URL.createObjectURL(audio),
    model: response.headers.get('X-Proteca-Voice-Model') ?? 'gemini-tts',
  };
}

export interface BrowserSpeechHandlers {
  onStart?: () => void;
  onEnd?: () => void;
}

/** Reserva sem cota: a voz do próprio navegador, em pt-BR. */
export function speakWithBrowser(text: string, handlers: BrowserSpeechHandlers = {}): boolean {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    return false;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'pt-BR';
  utterance.rate = 0.95;
  // Prefere uma voz instalada em português do Brasil, quando o sistema tiver.
  const voice = window.speechSynthesis
    .getVoices()
    .find((option) => option.lang.replace('_', '-').toLowerCase().startsWith('pt-br'));
  if (voice) utterance.voice = voice;
  utterance.onstart = () => handlers.onStart?.();
  utterance.onend = () => handlers.onEnd?.();
  utterance.onerror = () => handlers.onEnd?.();
  window.speechSynthesis.speak(utterance);
  return true;
}

/** Interrompe a voz do navegador, se estiver falando. */
export function stopBrowserSpeech(): void {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
}
