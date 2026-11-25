'use client';

// O mascote Proteca: um guardiãozinho em forma de escudo, com visor no rosto.
// O humor aparece na expressão e na cor; as animações ficam em globals.css
// (seção "Mascote Proteca") e param com prefers-reduced-motion.

import React, { useId } from 'react';
import type { ProtecaState } from '@/types';
import type { MascotHumor, ProtecaHumor } from '@/types/turma';

/** A API chama o guardião de `alerta`; a interface sempre mostra "Guardião". */
export function humorFromState(state: ProtecaState): ProtecaHumor {
  return state === 'alerta' ? 'guardiao' : state;
}

export const HUMOR_LABELS: Record<MascotHumor, string> = {
  acolhimento: 'Acolhimento',
  curiosidade: 'Curiosidade',
  guardiao: 'Guardião',
  neutro: 'Aguardando',
};

interface Palette {
  light: string;
  main: string;
  deep: string;
  dark: string;
  accent: string;
  cheek: string;
}

const PALETTES: Record<MascotHumor, Palette> = {
  // Verde-água
  acolhimento: { light: '#CCFBF1', main: '#2DD4BF', deep: '#14B8A6', dark: '#0F766E', accent: '#5EEAD4', cheek: '#FB7185' },
  // Âmbar
  curiosidade: { light: '#FEF3C7', main: '#FCC93A', deep: '#F59E0B', dark: '#B45309', accent: '#FDE047', cheek: '#FB7185' },
  // Coral
  guardiao: { light: '#FFE1D8', main: '#FF8C73', deep: '#F4664B', dark: '#B93A22', accent: '#FFB4A2', cheek: '#E11D48' },
  // Aguardando: cinza-azulado calmo
  neutro: { light: '#F1F5F9', main: '#BFCBDA', deep: '#94A3B8', dark: '#516074', accent: '#E2E8F0', cheek: '#FDA4AF' },
};

const INK = '#173D50';
const TONGUE = '#FB7185';

// Corpo em forma de escudo arredondado: o Proteca protege sem vigiar.
const BODY_PATH = 'M100 30 C142 30 170 52 170 92 C170 136 140 166 100 182 C60 166 30 136 30 92 C30 52 58 30 100 30 Z';

interface ProtecaMascotProps {
  /** Humor do Proteca; aceita também o `alerta` da API (vira guardião). */
  humor?: MascotHumor | ProtecaState;
  /** Largura e altura em pixels (uma classe de largura em `className` tem prioridade). */
  size?: number;
  /** Boca e corpo animados enquanto a voz do Proteca toca. */
  speaking?: boolean;
  className?: string;
  /** Texto para leitores de tela; por padrão descreve o humor. */
  label?: string;
  /** Quando o nome "Proteca" já está escrito ao lado, o desenho pode ser só decorativo. */
  decorative?: boolean;
}

export function ProtecaMascot({
  humor = 'acolhimento',
  size = 120,
  speaking = false,
  className = '',
  label,
  decorative = false,
}: ProtecaMascotProps) {
  const h: MascotHumor = humor === 'alerta' ? 'guardiao' : humor;
  const p = PALETTES[h];
  const gradientId = `pm-body-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;

  const ariaLabel =
    label ??
    `${h === 'neutro' ? 'Proteca aguardando' : `Proteca com humor ${HUMOR_LABELS[h].toLowerCase()}`}${
      speaking ? ', falando' : ''
    }`;

  const a11y = decorative
    ? { 'aria-hidden': true as const, focusable: 'false' as const }
    : { role: 'img', 'aria-label': ariaLabel };

  const classes = [
    'proteca-mascot',
    `proteca-mascot--${h}`,
    speaking ? 'proteca-mascot--speaking' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <svg viewBox="0 0 200 200" width={size} height={size} className={classes} {...a11y}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={p.light} />
          <stop offset="55%" stopColor={p.main} />
          <stop offset="100%" stopColor={p.deep} />
        </linearGradient>
      </defs>

      {/* Sombra no chão */}
      <ellipse cx="100" cy="192" rx="44" ry="5.5" fill="#0F172A" opacity="0.12" />

      <g className="pm-float">
        {/* Curiosidade inclina a cabeça */}
        <g transform={h === 'curiosidade' ? 'rotate(-6 100 110)' : undefined}>
          {/* Antena com luzinha */}
          <line x1="100" y1="32" x2="100" y2="17" stroke={p.dark} strokeWidth="4" strokeLinecap="round" />
          <circle className="pm-antenna-light" cx="100" cy="12" r="7" fill={p.accent} stroke={p.dark} strokeWidth="3" />

          {/* Braços atrás do corpo */}
          <ellipse cx="35" cy="120" rx="10" ry="17" transform="rotate(28 35 120)" fill={p.main} stroke={p.dark} strokeWidth="3" />
          {h === 'acolhimento' ? (
            // Acolhimento acena para a turma
            <g className="pm-wave-arm">
              <ellipse cx="171" cy="80" rx="9.5" ry="17" transform="rotate(30 171 80)" fill={p.main} stroke={p.dark} strokeWidth="3" />
            </g>
          ) : (
            <ellipse cx="165" cy="120" rx="10" ry="17" transform="rotate(-28 165 120)" fill={p.main} stroke={p.dark} strokeWidth="3" />
          )}

          {/* Corpo */}
          <path d={BODY_PATH} fill={`url(#${gradientId})`} stroke={p.dark} strokeWidth="3.5" strokeLinejoin="round" />
          <ellipse cx="100" cy="151" rx="30" ry="17" fill={p.light} opacity="0.55" />
          <ellipse cx="68" cy="55" rx="15" ry="7.5" transform="rotate(-32 68 55)" fill="#FFFFFF" opacity="0.5" />

          {/* Visor do rosto */}
          <rect x="52" y="60" width="96" height="66" rx="33" fill="#FFFFFF" fillOpacity="0.96" stroke={p.dark} strokeOpacity="0.25" strokeWidth="2" />

          <Brows humor={h} />
          <g className="pm-eyes">
            <Eyes humor={h} />
          </g>

          {/* Bochechas */}
          <ellipse cx="64" cy="106" rx="7" ry="4.5" fill={p.cheek} opacity="0.45" />
          <ellipse cx="136" cy="106" rx="7" ry="4.5" fill={p.cheek} opacity="0.45" />

          {speaking ? (
            <g className="pm-mouth-talk">
              <ellipse cx="100" cy="111" rx="10" ry="8" fill={INK} />
              <ellipse cx="100" cy="115.5" rx="6" ry="3" fill={TONGUE} />
            </g>
          ) : (
            <Mouth humor={h} />
          )}

          {h === 'curiosidade' && <Magnifier palette={p} />}
          {h === 'guardiao' && <Shield palette={p} />}
          {h === 'neutro' && <WaitingDots color={p.dark} />}
        </g>

        {/* Ondas de som enquanto fala (sem animação, ficam paradas e visíveis) */}
        {speaking && (
          <g fill="none" stroke={p.dark} strokeWidth="4" strokeLinecap="round">
            <path className="pm-sound" d="M22 64 Q14 77 22 90" />
            <path className="pm-sound" d="M11 55 Q-1 77 11 99" style={{ animationDelay: '0.25s' }} />
          </g>
        )}
      </g>
    </svg>
  );
}

function Eyes({ humor }: { humor: MascotHumor }) {
  if (humor === 'curiosidade') {
    // Olhar para cima e para o lado; o olho direito aparece aumentado pela lupa.
    return (
      <>
        <ellipse cx="83" cy="88" rx="8" ry="10.5" fill={INK} />
        <circle cx="85.5" cy="83.5" r="3" fill="#FFFFFF" />
        <ellipse cx="124" cy="87" rx="10.5" ry="13" fill={INK} />
        <circle cx="127.5" cy="81.5" r="4" fill="#FFFFFF" />
        <circle cx="121" cy="92" r="1.8" fill="#FFFFFF" />
      </>
    );
  }

  const cy = humor === 'guardiao' ? 93 : 90;
  const ry = humor === 'guardiao' ? 9 : 10;

  return (
    <>
      {[80, 120].map((cx) => (
        <g key={cx}>
          <ellipse cx={cx} cy={cy} rx="8" ry={ry} fill={INK} />
          <circle cx={cx - 2.5} cy={cy - 4} r="3" fill="#FFFFFF" />
          <circle cx={cx + 2.5} cy={cy + 3} r="1.4" fill="#FFFFFF" />
          {/* Olhos sorridentes: a pálpebra de baixo corta o olho em meia-lua */}
          {humor === 'acolhimento' && <ellipse cx={cx} cy={cy + 10.5} rx="11" ry="6.5" fill="#FFFFFF" />}
        </g>
      ))}
    </>
  );
}

function Brows({ humor }: { humor: MascotHumor }) {
  const common = { fill: 'none', stroke: INK, strokeLinecap: 'round' as const };

  if (humor === 'acolhimento') {
    return (
      <g {...common} strokeWidth="3">
        <path d="M71 75 Q80 69 89 74" />
        <path d="M111 74 Q120 69 129 75" />
      </g>
    );
  }
  if (humor === 'curiosidade') {
    // Uma sobrancelha erguida bem alto: "hum, o que será?"
    return (
      <g {...common} strokeWidth="3.5">
        <path d="M72 71 Q81 61 92 68" />
      </g>
    );
  }
  if (humor === 'guardiao') {
    // Firme e atento, sem cara de bravo
    return (
      <g {...common} strokeWidth="4">
        <path d="M69 75 L89 80" />
        <path d="M131 75 L111 80" />
      </g>
    );
  }
  return null;
}

function Mouth({ humor }: { humor: MascotHumor }) {
  if (humor === 'acolhimento') {
    return (
      <g>
        <path d="M83 106 C87 121 113 121 117 106 Z" fill={INK} stroke={INK} strokeWidth="2" strokeLinejoin="round" />
        <path d="M91 114 Q100 108 109 114 Q100 119 91 114 Z" fill={TONGUE} />
      </g>
    );
  }
  if (humor === 'curiosidade') {
    return <ellipse cx="103" cy="111" rx="5.5" ry="6.5" fill={INK} />;
  }
  if (humor === 'guardiao') {
    return <path d="M85 107 Q100 121 115 107" fill="none" stroke={INK} strokeWidth="4" strokeLinecap="round" />;
  }
  return <path d="M91 110 Q100 116 109 110" fill="none" stroke={INK} strokeWidth="3.5" strokeLinecap="round" />;
}

function Magnifier({ palette }: { palette: Palette }) {
  return (
    <g>
      {/* Lupa na frente do olho direito */}
      <line x1="136" y1="100" x2="151" y2="118" stroke={palette.dark} strokeWidth="7" strokeLinecap="round" />
      <circle cx="124" cy="87" r="17" fill="#E0F2FE" fillOpacity="0.3" stroke={palette.dark} strokeWidth="4.5" />
      <path d="M113 80 Q116 74 122 72" fill="none" stroke="#FFFFFF" strokeWidth="3" strokeLinecap="round" opacity="0.9" />
      <circle cx="152" cy="120" r="8" fill={palette.main} stroke={palette.dark} strokeWidth="3" />
      {/* Interrogação ao lado da cabeça */}
      <text x="40" y="44" fontSize="30" fontWeight="900" fill={palette.dark} fontFamily="system-ui, sans-serif">
        ?
      </text>
    </g>
  );
}

function Shield({ palette }: { palette: Palette }) {
  return (
    <g>
      {/* Escudo à frente do corpo, com um "tudo certo" no meio */}
      <path
        d="M132 122 C141 127 149 128 155 127 L155 146 C155 160 145 169 132 175 C119 169 109 160 109 146 L109 127 C115 128 123 127 132 122 Z"
        fill="#FFF7ED"
        stroke={palette.dark}
        strokeWidth="3.5"
        strokeLinejoin="round"
      />
      <path
        d="M114 131 C120 131 126 130 132 127 C138 130 144 131 150 131 L150 146 C150 157 142 164 132 169 C122 164 114 157 114 146 Z"
        fill="none"
        stroke={palette.accent}
        strokeWidth="2"
      />
      <path d="M120 147 L129 156 L145 138" fill="none" stroke={palette.deep} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="110" cy="150" r="7.5" fill={palette.main} stroke={palette.dark} strokeWidth="3" />
    </g>
  );
}

function WaitingDots({ color }: { color: string }) {
  return (
    <g fill={color}>
      {[0, 1, 2].map((index) => (
        <circle
          key={index}
          className="pm-dot"
          cx={138 + index * 12}
          cy={30 - index * 5}
          r="4.5"
          style={{ animationDelay: `${index * 0.2}s` }}
        />
      ))}
    </g>
  );
}
