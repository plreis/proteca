// frontend/src/services/voiceService.ts

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

  if (!response.ok) {
    throw new Error(`Voz indisponível (status ${response.status}).`);
  }

  const audio = await response.blob();
  return {
    audioUrl: URL.createObjectURL(audio),
    model: response.headers.get('X-Proteca-Voice-Model') ?? 'gemini-tts',
  };
}

/** Reserva sem cota: a voz do próprio navegador, em pt-BR. */
export function speakWithBrowser(text: string): boolean {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    return false;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'pt-BR';
  utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
  return true;
}
