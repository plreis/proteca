'use client';

// Código da turma em destaque na sessão aberta: é com ele que a turma abre a tela
// da turma, sem login e sem coleta de dados (ADR 0004).

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { ProtecaMascot } from '@/components/ProtecaMascot';

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

interface ClassCodeCardProps {
  classCode?: string;
}

export function ClassCodeCard({ classCode }: ClassCodeCardProps) {
  const [origin, setOrigin] = useState<string | null>(null);
  const [copyNote, setCopyNote] = useState<string | null>(null);

  const directPath = classCode ? `/turma/?codigo=${encodeURIComponent(classCode)}` : '/turma/';

  // O endereço completo só existe no navegador (o site é exportado como estático).
  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  useEffect(() => {
    if (!copyNote) return;
    const timeoutId = window.setTimeout(() => setCopyNote(null), 2500);
    return () => window.clearTimeout(timeoutId);
  }, [copyNote]);

  const directUrl = origin ? `${origin}${BASE_PATH}${directPath}` : null;
  const shortAddress = origin ? `${origin.replace(/^https?:\/\//, '')}${BASE_PATH}/turma/` : null;

  const handleCopy = async () => {
    if (!directUrl) return;
    try {
      await navigator.clipboard.writeText(directUrl);
      setCopyNote('Link copiado!');
    } catch {
      setCopyNote('Não deu para copiar. Use o botão para abrir a tela da turma.');
    }
  };

  return (
    <section className="rounded-2xl border-2 border-brand-action/25 bg-gradient-to-br from-brand-action-light via-white to-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <ProtecaMascot humor="acolhimento" size={52} decorative className="shrink-0" />
        <div>
          <h2 className="text-base font-bold text-brand-text">Tela da turma</h2>
          <p className="text-xs text-brand-muted">Para o projetor ou os tablets da turma</p>
        </div>
      </div>

      {classCode ? (
        <>
          <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-brand-muted">Código da turma</p>
          <div
            className="mt-1.5 flex gap-1.5"
            role="text"
            aria-label={`Código da turma: ${classCode.split('').join(' ')}`}
          >
            {classCode.split('').map((char, index) => (
              <span
                key={`${char}-${index}`}
                aria-hidden="true"
                className="flex h-12 w-10 items-center justify-center rounded-lg border-2 border-brand-action/30 bg-white font-mono text-2xl font-black text-brand-primary shadow-sm"
              >
                {char}
              </span>
            ))}
          </div>

          <p className="mt-4 text-sm leading-relaxed text-slate-600">
            Na tela da turma, todos veem o Proteca e as intervenções que você decidir mostrar.{' '}
            <strong className="text-brand-text">Sem login e sem coleta de dados.</strong>
          </p>
          {shortAddress && (
            <p className="mt-2 text-xs text-slate-500">
              Ou abra <span className="font-mono font-semibold text-brand-text">{shortAddress}</span> e digite o código.
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Link
              href={directPath}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-action px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-action-hover"
            >
              Abrir a tela da turma
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
              </svg>
              <span className="sr-only">(abre em nova aba)</span>
            </Link>
            <button
              type="button"
              onClick={handleCopy}
              disabled={!directUrl}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Copiar link
            </button>
          </div>
          {copyNote && (
            <p role="status" className="mt-2 text-xs font-semibold text-brand-action">
              {copyNote}
            </p>
          )}
        </>
      ) : (
        <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
          O código da turma ainda não chegou da API. Atualize a página em instantes.
        </p>
      )}
    </section>
  );
}
