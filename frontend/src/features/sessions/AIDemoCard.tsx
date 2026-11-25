'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { LiveGuidance, ProtecaIntervention, ProtecaState } from '@/types';
import { useSchool } from '@/context/SchoolContext';
import { requestProtecaVoice, speakWithBrowser, stopBrowserSpeech } from '@/services/voiceService';
import { clearClassScreen, showOnClassScreen } from '@/services/turmaService';
import { ApiError } from '@/services/api';
import { HUMOR_LABELS, ProtecaMascot, humorFromState } from '@/components/ProtecaMascot';

interface AIDemoCardProps {
  sessionId: string;
}

const stateStyles: Record<ProtecaState, string> = {
  acolhimento: 'from-teal-400/25 to-cyan-400/10 border-teal-300/40',
  curiosidade: 'from-amber-400/25 to-yellow-300/10 border-amber-300/40',
  alerta: 'from-[#FF8C73]/30 to-orange-400/10 border-[#FFB4A2]/40',
};

/** O que aconteceu com a última ação do professor sobre a tela da turma. */
type ClassScreenAction =
  | { status: 'idle' }
  | { status: 'sending' }
  | { status: 'sent'; at: string }
  | { status: 'clearing' }
  | { status: 'cleared'; at: string }
  | { status: 'error'; message: string };

/** Texto que a voz do Proteca lê: a fala curta, ou mensagem e pergunta quando ela não vier. */
function speechText(intervention: ProtecaIntervention): string {
  return intervention.speech?.trim() || `${intervention.message} ${intervention.prompt}`;
}

function formatTime(iso?: string | null): string {
  const date = iso ? new Date(iso) : new Date();
  const valid = Number.isNaN(date.getTime()) ? new Date() : date;
  return valid.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function describeClassScreenError(err: unknown): string {
  if (err instanceof ApiError) {
    const generic = err.message.startsWith('A API respondeu com o status');
    if (err.status === 409 && generic) {
      return 'Esta sessão já foi encerrada; a tela da turma não recebe mais intervenções.';
    }
    return err.message;
  }
  if (err instanceof TypeError) {
    return 'Sem conexão com a API. Verifique a internet e tente de novo.';
  }
  return err instanceof Error ? err.message : 'Não foi possível falar com a tela da turma.';
}

export const AIDemoCard: React.FC<AIDemoCardProps> = ({ sessionId }) => {
  const { requestLiveGuidance } = useSchool();
  const [guidance, setGuidance] = useState<LiveGuidance | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAutoMode, setIsAutoMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voice, setVoice] = useState<{ audioUrl: string; label: string } | null>(null);
  const [voiceNote, setVoiceNote] = useState<string | null>(null);
  const [isPreparingVoice, setIsPreparingVoice] = useState(false);
  const [isVoicePlaying, setIsVoicePlaying] = useState(false);
  const [classAction, setClassAction] = useState<ClassScreenAction>({ status: 'idle' });
  const [onClassScreen, setOnClassScreen] = useState<{ title: string; at: string } | null>(null);

  // Libera o áudio anterior da memória ao trocar de orientação ou sair da tela.
  useEffect(() => {
    return () => {
      if (voice) URL.revokeObjectURL(voice.audioUrl);
    };
  }, [voice]);

  // Ao sair da tela, a voz do navegador também para.
  useEffect(() => () => stopBrowserSpeech(), []);

  const handleSpeak = async (text: string) => {
    setIsPreparingVoice(true);
    setVoiceNote(null);
    stopBrowserSpeech();
    try {
      const result = await requestProtecaVoice(text);
      setVoice({ audioUrl: result.audioUrl, label: `Voz: ${result.model}` });
    } catch {
      setVoice(null);
      setVoiceNote(
        speakWithBrowser(text, {
          onStart: () => setIsVoicePlaying(true),
          onEnd: () => setIsVoicePlaying(false),
        })
          ? 'Voz do Gemini indisponível agora; lendo com a voz do navegador.'
          : 'Áudio indisponível neste navegador.'
      );
    } finally {
      setIsPreparingVoice(false);
    }
  };

  const handleGenerate = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setGuidance(await requestLiveGuidance(sessionId));
      stopBrowserSpeech();
      setVoice(null);
      setVoiceNote(null);
      setIsVoicePlaying(false);
      // Intervenção nova ainda não foi para a turma; a anterior continua lá até o professor decidir.
      setClassAction({ status: 'idle' });
    } catch (err) {
      const detail = err instanceof Error ? ` (${err.message})` : '';
      setError(`Não foi possível gerar a orientação agora${detail}. Tente novamente.`);
    } finally {
      setIsLoading(false);
    }
  }, [requestLiveGuidance, sessionId]);

  useEffect(() => {
    if (!isAutoMode) return;
    const intervalId = window.setInterval(() => {
      void handleGenerate();
    }, 120000);
    return () => window.clearInterval(intervalId);
  }, [isAutoMode, handleGenerate]);

  const handleShowToClass = async (intervention: ProtecaIntervention) => {
    setClassAction({ status: 'sending' });
    try {
      const screen = await showOnClassScreen(sessionId, intervention);
      const at = formatTime(screen.broadcastAt);
      setClassAction({ status: 'sent', at });
      setOnClassScreen({ title: intervention.title, at });
    } catch (err) {
      setClassAction({ status: 'error', message: describeClassScreenError(err) });
    }
  };

  const handleClearClassScreen = async () => {
    setClassAction({ status: 'clearing' });
    try {
      await clearClassScreen(sessionId);
      setClassAction({ status: 'cleared', at: formatTime() });
      setOnClassScreen(null);
    } catch (err) {
      setClassAction({ status: 'error', message: describeClassScreenError(err) });
    }
  };

  const intervention = guidance?.intervention;
  const isClassBusy = classAction.status === 'sending' || classAction.status === 'clearing';

  return (
    <section className="proteca-panel rounded-2xl border border-slate-700 bg-gradient-to-br from-slate-950 via-brand-primary to-slate-900 p-5 text-white shadow-lg sm:p-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-5">
        <div className="flex items-start gap-3">
          <ProtecaMascot humor="acolhimento" size={56} decorative className="-mt-1 shrink-0" />
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-300">Proteca Live</p>
            <h3 className="mt-1 text-xl font-bold">Foco, segurança e curiosidade</h3>
            <p className="mt-1 max-w-xl text-xs leading-relaxed text-slate-300">
              Apoio ao professor com sinais agregados e sugestões formativas. A decisão continua humana.
            </p>
          </div>
        </div>
        <span className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-3 py-1 text-xs font-bold text-emerald-200">
          Sem vigilância invasiva
        </span>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_auto]">
        <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
          <strong className="mb-1 block text-amber-200">Modo de acompanhamento</strong>
          {isAutoMode ? 'Proteca fará uma leitura agregada a cada 2 minutos.' : 'Faça uma leitura quando quiser mudar o ritmo da aula.'}
        </div>
        <button
          type="button"
          onClick={() => setIsAutoMode((current) => !current)}
          className="rounded-xl border border-white/20 px-4 py-3 text-sm font-bold transition hover:bg-white/10"
          aria-pressed={isAutoMode}
        >
          {isAutoMode ? 'Pausar Live' : 'Ativar a cada 2 min'}
        </button>
      </div>

      {!guidance && !isLoading && (
        <div className="rounded-xl border border-dashed border-white/20 bg-white/5 p-6 text-center">
          <p className="mb-4 text-sm text-slate-300">
            O que está acontecendo na turma agora? Peça uma sugestão sem interromper o fluxo.
          </p>
          <button
            type="button"
            onClick={handleGenerate}
            className="rounded-xl bg-amber-300 px-4 py-2.5 text-sm font-bold text-slate-950 shadow transition hover:bg-amber-200"
          >
            Ler o momento da aula
          </button>
        </div>
      )}

      {isLoading && (
        <div className="flex flex-col items-center gap-2 rounded-xl bg-white/5 py-8 text-sm text-slate-300" role="status">
          <ProtecaMascot humor="curiosidade" size={72} decorative />
          <span>Proteca está organizando uma sugestão...</span>
        </div>
      )}

      {error && <p className="mt-3 rounded-lg bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}

      {guidance && !isLoading && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-amber-300">Leitura do momento</p>
              <p className="mt-1 text-lg font-bold capitalize">{guidance.attentionLevel}</p>
            </div>
            <span className="rounded-full border border-white/20 px-3 py-1 text-xs text-slate-300">
              {guidance.isMock ? 'Orientação de reserva' : guidance.model}
            </span>
          </div>

          <p className="rounded-xl bg-white/10 p-4 text-sm leading-relaxed text-slate-100">{guidance.observedPattern}</p>

          <div className="grid gap-2 sm:grid-cols-2">
            {guidance.teacherSuggestions.map((suggestion, index) => (
              <div key={suggestion} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-200">
                <span className="mr-2 font-bold text-amber-300">{index + 1}.</span>
                {suggestion}
              </div>
            ))}
          </div>

          {intervention && (
            <div className={`rounded-2xl border bg-gradient-to-br p-4 ${stateStyles[intervention.state]}`}>
              <div className="flex items-start gap-3">
                <ProtecaMascot
                  humor={intervention.state}
                  size={76}
                  speaking={isVoicePlaying}
                  className="-ml-1 shrink-0"
                />
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wider text-white/70">
                    Prévia para a turma · {HUMOR_LABELS[humorFromState(intervention.state)]}
                  </p>
                  <h4 className="mt-1 font-bold">{intervention.title}</h4>
                  <p className="mt-1 text-sm text-white/90">{intervention.message}</p>
                  <p className="mt-3 rounded-lg bg-black/10 p-2 text-sm font-medium text-white">{intervention.prompt}</p>
                  {intervention.speech && (
                    <p className="mt-3 text-xs leading-relaxed text-white/80">
                      <span className="font-bold">Fala do Proteca:</span> “{intervention.speech}”
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => handleSpeak(speechText(intervention))}
                  disabled={isPreparingVoice}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-white/90 px-3 py-1.5 text-xs font-bold text-slate-900 hover:bg-white disabled:cursor-wait disabled:opacity-60"
                >
                  <SpeakerIcon />
                  {isPreparingVoice ? 'Preparando a voz...' : 'Ouvir o Proteca'}
                </button>
                {voice && <span className="text-[11px] text-white/70">{voice.label}</span>}
              </div>
              {voice && (
                <audio
                  key={voice.audioUrl}
                  src={voice.audioUrl}
                  controls
                  autoPlay
                  className="mt-2 w-full"
                  onPlay={() => setIsVoicePlaying(true)}
                  onPause={() => setIsVoicePlaying(false)}
                  onEnded={() => setIsVoicePlaying(false)}
                />
              )}
              {voiceNote && <p className="mt-2 text-[11px] text-white/80">{voiceNote}</p>}
            </div>
          )}

          {/* A turma só vê o que o professor decidir mostrar */}
          <div className="rounded-2xl border border-white/15 bg-white/5 p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-amber-300">Tela da turma</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {intervention && (
                <button
                  type="button"
                  onClick={() => handleShowToClass(intervention)}
                  disabled={isClassBusy}
                  className="inline-flex items-center gap-2 rounded-xl bg-amber-300 px-4 py-2.5 text-sm font-bold text-slate-950 shadow transition hover:bg-amber-200 disabled:cursor-wait disabled:opacity-60"
                >
                  <ScreenIcon />
                  {classAction.status === 'sending'
                    ? 'Enviando para a turma...'
                    : classAction.status === 'sent'
                      ? 'Mostrar de novo'
                      : 'Mostrar para a turma'}
                </button>
              )}
              <button
                type="button"
                onClick={handleClearClassScreen}
                disabled={isClassBusy}
                className="rounded-xl border border-white/25 px-3 py-2 text-xs font-bold text-slate-200 transition hover:bg-white/10 disabled:cursor-wait disabled:opacity-60"
              >
                {classAction.status === 'clearing' ? 'Limpando...' : 'Limpar tela da turma'}
              </button>
            </div>
            <ClassActionStatus action={classAction} onClassScreen={onClassScreen} />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3">
            <p className="max-w-2xl text-[11px] leading-relaxed text-slate-400">{guidance.limitations}</p>
            <button type="button" onClick={handleGenerate} className="text-xs font-bold text-amber-300 underline hover:text-amber-200">
              Ler novamente
            </button>
          </div>
        </div>
      )}
    </section>
  );
};

function ClassActionStatus({
  action,
  onClassScreen,
}: {
  action: ClassScreenAction;
  onClassScreen: { title: string; at: string } | null;
}) {
  let content: React.ReactNode;
  let tone = 'text-slate-300';

  switch (action.status) {
    case 'sending':
      content = 'Enviando a intervenção para a tela da turma...';
      break;
    case 'clearing':
      content = 'Limpando a tela da turma...';
      break;
    case 'sent':
      tone = 'text-emerald-200';
      content = (
        <>
          <span aria-hidden="true">✓ </span>
          Enviado às <strong>{action.at}</strong>. A turma já está vendo esta intervenção.
        </>
      );
      break;
    case 'cleared':
      tone = 'text-emerald-200';
      content = `Tela da turma limpa às ${action.at}. O Proteca voltou a aguardar.`;
      break;
    case 'error':
      tone = 'text-rose-200';
      content = action.message;
      break;
    default:
      content = onClassScreen
        ? `Na tela da turma agora: “${onClassScreen.title}” (desde ${onClassScreen.at}).`
        : 'A turma só vê uma intervenção quando você decidir mostrar.';
  }

  return (
    <p role={action.status === 'error' ? 'alert' : 'status'} className={`mt-2 text-xs leading-relaxed ${tone}`}>
      {content}
    </p>
  );
}

function SpeakerIcon() {
  return (
    <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M11 5 6 9H3v6h3l5 4V5Z" />
      <path strokeLinecap="round" d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" />
    </svg>
  );
}

function ScreenIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path strokeLinecap="round" d="M8 20h8M12 16v4" />
    </svg>
  );
}
