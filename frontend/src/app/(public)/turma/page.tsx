'use client';

// Tela da turma (ADR 0004): pública, sem login, sem cookies, sem localStorage e sem
// enviar dados. Só lê a intervenção que o professor decidiu enviar e toca a voz.

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ProtecaMascot, humorFromState } from '@/components/ProtecaMascot';
import { ApiError } from '@/services/api';
import {
  CLASS_CODE_LENGTH,
  fetchClassScreen,
  fetchClassVoice,
  normalizeClassCode,
} from '@/services/turmaService';
import { speakWithBrowser, stopBrowserSpeech } from '@/services/voiceService';
import type { ProtecaIntervention } from '@/types';
import type { ClassScreen } from '@/types/turma';

const POLL_INTERVAL_MS = 4000;
const VOICE_WAIT_MS = 8000;

type Connection = 'loading' | 'ok' | 'invalid' | 'offline';

function speechText(intervention: ProtecaIntervention): string {
  return intervention.speech?.trim() || `${intervention.message} ${intervention.prompt}`;
}

function CodeEntry({ onSubmit, notice }: { onSubmit: (code: string) => void; notice?: string }) {
  const [value, setValue] = useState('');
  const ready = value.length === CLASS_CODE_LENGTH;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (ready) onSubmit(value);
      }}
      className="mx-auto flex w-full max-w-xl flex-col items-center gap-5 text-center"
    >
      <ProtecaMascot humor="neutro" size={160} />
      <h1 className="text-3xl font-black text-brand-text sm:text-4xl">Tela da turma</h1>
      <p className="text-lg text-slate-600">Digite o código que o professor mostrou.</p>
      {notice && (
        <p role="alert" className="rounded-xl bg-amber-50 px-4 py-2 text-base font-semibold text-amber-800">
          {notice}
        </p>
      )}
      <label htmlFor="codigo-turma" className="sr-only">
        Código da turma
      </label>
      <input
        id="codigo-turma"
        value={value}
        onChange={(event) => setValue(normalizeClassCode(event.target.value))}
        inputMode="text"
        autoComplete="off"
        autoCapitalize="characters"
        autoCorrect="off"
        spellCheck={false}
        maxLength={CLASS_CODE_LENGTH}
        placeholder="AULA8B"
        className="w-full rounded-2xl border-4 border-brand-action/40 bg-white px-4 py-4 text-center font-mono text-5xl font-black uppercase tracking-[0.3em] text-brand-primary placeholder:text-slate-300 focus:border-brand-action focus:outline-none"
      />
      <button
        type="submit"
        disabled={!ready}
        className="w-full rounded-2xl bg-brand-action px-6 py-4 text-2xl font-bold text-white shadow-md hover:bg-brand-action-hover disabled:opacity-40"
      >
        Entrar
      </button>
    </form>
  );
}

function Waiting({ objective }: { objective?: string }) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center gap-5 text-center">
      <ProtecaMascot humor="neutro" size={260} />
      <h1 className="text-4xl font-black text-brand-text sm:text-5xl">Aguardando o professor</h1>
      <p className="text-xl text-slate-600">O Proteca aparece aqui quando o professor enviar uma mensagem.</p>
      {objective && (
        <p className="rounded-2xl bg-white px-5 py-3 text-lg text-slate-700 shadow-sm">
          <span className="block text-xs font-bold uppercase tracking-wider text-brand-muted">
            Objetivo da aula
          </span>
          {objective}
        </p>
      )}
    </div>
  );
}

function InterventionView({
  intervention,
  speaking,
}: {
  intervention: ProtecaIntervention;
  speaking: boolean;
}) {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col items-center gap-6 text-center lg:flex-row lg:items-center lg:gap-12 lg:text-left">
      <ProtecaMascot humor={humorFromState(intervention.state)} size={320} speaking={speaking} className="shrink-0" />
      <div className="space-y-5" aria-live="polite">
        <h1 className="text-4xl font-black leading-tight text-brand-text sm:text-6xl">{intervention.title}</h1>
        <p className="text-2xl leading-relaxed text-slate-700 sm:text-4xl">{intervention.message}</p>
        <p className="rounded-2xl bg-white px-6 py-4 text-2xl font-bold text-brand-primary shadow-sm sm:text-4xl">
          {intervention.prompt}
        </p>
      </div>
    </div>
  );
}

export default function ClassScreenPage() {
  const [code, setCode] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [screen, setScreen] = useState<ClassScreen | null>(null);
  const [connection, setConnection] = useState<Connection>('loading');
  const [soundOn, setSoundOn] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const soundOnRef = useRef(false);
  const handledBroadcast = useRef<string | null>(null);
  const waitTimer = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // O código vem de ?codigo=; o site é estático, então só dá para ler no navegador.
  useEffect(() => {
    const fromUrl = normalizeClassCode(new URLSearchParams(window.location.search).get('codigo') ?? '');
    setCode(fromUrl.length === CLASS_CODE_LENGTH ? fromUrl : null);
    setReady(true);
  }, []);

  // Consulta a cada 4 s; erro de rede mantém a última tela e tenta de novo.
  useEffect(() => {
    if (!code) return;
    let cancelled = false;
    let timeoutId: number | undefined;
    let controller: AbortController | null = null;

    const poll = async () => {
      controller = new AbortController();
      let keepPolling = true;
      try {
        const data = await fetchClassScreen(code, controller.signal);
        if (cancelled) return;
        setScreen(data);
        setConnection('ok');
        if (data.sessionStatus === 'encerrada') keepPolling = false;
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 404) {
          setConnection('invalid');
          keepPolling = false;
        } else {
          setConnection('offline');
        }
      }
      if (!cancelled && keepPolling) timeoutId = window.setTimeout(poll, POLL_INTERVAL_MS);
    };

    poll();
    return () => {
      cancelled = true;
      controller?.abort();
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [code]);

  const clearWait = () => {
    if (waitTimer.current !== null) {
      window.clearTimeout(waitTimer.current);
      waitTimer.current = null;
    }
  };

  const speakFallback = useCallback((intervention: ProtecaIntervention) => {
    const started = speakWithBrowser(speechText(intervention), {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    });
    if (!started) setSpeaking(false);
  }, []);

  const playVoice = useCallback(
    async (intervention: ProtecaIntervention) => {
      if (!code) return;
      try {
        const voice = await fetchClassVoice(code);
        if (!voice) throw new Error('sem áudio');
        stopBrowserSpeech();
        audioRef.current?.pause();
        const audio = new Audio(voice.audioUrl);
        audioRef.current = audio;
        const finish = () => {
          setSpeaking(false);
          URL.revokeObjectURL(voice.audioUrl);
        };
        audio.onended = finish;
        audio.onerror = () => {
          finish();
          speakFallback(intervention);
        };
        await audio.play();
        setSpeaking(true);
      } catch {
        speakFallback(intervention);
      }
    },
    [code, speakFallback]
  );

  // Fala quando o professor envia algo novo (broadcast_at muda) e o som está ativado.
  useEffect(() => {
    if (!soundOn || !screen?.broadcastAt || !screen.intervention) return;
    const { broadcastAt, intervention, audioReady } = screen;
    if (handledBroadcast.current === broadcastAt) return;

    if (audioReady) {
      clearWait();
      handledBroadcast.current = broadcastAt;
      void playVoice(intervention);
    } else if (waitTimer.current === null) {
      // O áudio ainda está sendo gerado: espera um pouco e usa a voz do navegador.
      waitTimer.current = window.setTimeout(() => {
        waitTimer.current = null;
        if (handledBroadcast.current === broadcastAt || !soundOnRef.current) return;
        handledBroadcast.current = broadcastAt;
        speakFallback(intervention);
      }, VOICE_WAIT_MS);
    }
  }, [soundOn, screen, playVoice, speakFallback]);

  // Uma intervenção nova ou retirada cancela a espera e a fala anteriores.
  const broadcastAt = screen?.broadcastAt ?? null;
  useEffect(() => {
    clearWait();
    audioRef.current?.pause();
    stopBrowserSpeech();
    setSpeaking(false);
  }, [broadcastAt]);

  useEffect(
    () => () => {
      clearWait();
      audioRef.current?.pause();
      stopBrowserSpeech();
    },
    []
  );

  const enableSound = () => {
    // Só fala o que chegar depois; o clique libera o áudio do navegador.
    handledBroadcast.current = screen?.broadcastAt ?? null;
    soundOnRef.current = true;
    setSoundOn(true);
  };

  const handleCode = (value: string) => {
    window.history.replaceState(null, '', `?codigo=${encodeURIComponent(value)}`);
    setConnection('loading');
    setScreen(null);
    setCode(value);
  };

  let content: React.ReactNode;
  if (!ready) {
    content = null;
  } else if (!code) {
    content = <CodeEntry onSubmit={handleCode} />;
  } else if (connection === 'invalid') {
    content = (
      <CodeEntry
        onSubmit={handleCode}
        notice="Não encontramos esse código. Confira com o professor e tente de novo."
      />
    );
  } else if (!screen) {
    content = (
      <div className="flex flex-col items-center gap-4 text-center" role="status">
        <ProtecaMascot humor="neutro" size={200} />
        <p className="text-2xl font-bold text-slate-600">
          {connection === 'offline' ? 'Sem conexão. Tentando de novo…' : 'Carregando…'}
        </p>
      </div>
    );
  } else if (screen.sessionStatus === 'encerrada') {
    content = (
      <div className="flex flex-col items-center gap-5 text-center">
        <ProtecaMascot humor="acolhimento" size={240} />
        <h1 className="text-4xl font-black text-brand-text sm:text-5xl">Sessão encerrada</h1>
        <p className="text-xl text-slate-600">Obrigado pela aula! O Proteca se despede até a próxima.</p>
      </div>
    );
  } else if (screen.intervention) {
    content = <InterventionView intervention={screen.intervention} speaking={speaking} />;
  } else {
    content = <Waiting objective={screen.objective} />;
  }

  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-b from-brand-action-light via-white to-white px-5 py-6 sm:px-10">
      <div className="flex min-h-[3rem] items-center justify-between gap-3">
        <span className="text-lg font-black text-brand-primary">Proteca</span>
        {code && screen && screen.sessionStatus === 'aberta' && (
          <div className="flex items-center gap-3">
            {connection === 'offline' && (
              <span role="status" className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-800">
                Sem conexão, tentando de novo…
              </span>
            )}
            {!soundOn ? (
              <button
                type="button"
                onClick={enableSound}
                className="rounded-xl bg-brand-action px-5 py-3 text-lg font-bold text-white shadow-md hover:bg-brand-action-hover"
              >
                Ativar o som
              </button>
            ) : (
              <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-slate-600 shadow-sm">
                Som ativado
              </span>
            )}
          </div>
        )}
      </div>
      <div className="flex flex-1 items-center justify-center py-6">{content}</div>
    </main>
  );
}
