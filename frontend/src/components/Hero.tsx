import { lazy, Suspense, useEffect, useState } from 'react';
import { SuggestionCards } from './SuggestionCards';

// Lazy-load the 3D scene so the chat loads fast.
const HeroScene = lazy(() => import('./three/HeroScene'));

interface Props {
  onCardClick: (question: string) => void;
}

export function Hero({ onCardClick }: Props) {
  const [webglAvailable, setWebglAvailable] = useState(true);

  useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const gl =
        canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      setWebglAvailable(!!gl);
    } catch {
      setWebglAvailable(false);
    }
  }, []);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
        {/* Hero: heading + 3D visual */}
        <div className="grid grid-cols-1 items-center gap-6 lg:grid-cols-2 lg:gap-12">
          {/* Text column */}
          <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary-light px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-wider text-primary">
              AI-Powered Campus Assistant
            </div>

            <h1 className="font-display text-3xl font-bold leading-tight text-text sm:text-4xl lg:text-[2.75rem]">
              Your MITS knowledge,
              <br />
              <span className="text-primary">one conversation away.</span>
            </h1>

            <p className="mt-4 max-w-md text-sm leading-relaxed text-text-muted sm:text-base">
              Ask about academics, faculty, fees, placements, departments,
              examinations and campus information.
            </p>

            <div className="mt-3 text-[0.8rem] font-medium text-text-muted">
              Madhav Institute of Technology &amp; Science, Gwalior
            </div>
          </div>

          {/* 3D visual column */}
          <div className="hero-canvas-container h-[260px] sm:h-[320px] lg:h-[380px]">
            {webglAvailable ? (
              <Suspense fallback={<HeroFallback />}>
                <HeroScene />
              </Suspense>
            ) : (
              <HeroFallback />
            )}
          </div>
        </div>

        {/* Suggestion cards */}
        <div className="mt-10 sm:mt-14">
          <SuggestionCards onCardClick={onCardClick} />
        </div>
      </div>
    </div>
  );
}

/** Static SVG fallback shown when WebGL is unavailable or the 3D scene is loading. */
function HeroFallback() {
  return (
    <div className="flex h-full items-center justify-center">
      <svg
        width="200"
        height="200"
        viewBox="0 0 200 200"
        fill="none"
        aria-hidden="true"
      >
        {/* Central core */}
        <circle
          cx="100"
          cy="100"
          r="28"
          fill="var(--primary)"
          opacity="0.08"
        />
        <circle
          cx="100"
          cy="100"
          r="32"
          fill="none"
          stroke="var(--primary)"
          strokeWidth="1.2"
          opacity="0.5"
        />
        <circle
          cx="100"
          cy="100"
          r="20"
          fill="none"
          stroke="var(--primary)"
          strokeWidth="0.8"
          opacity="0.3"
        />

        {/* Nodes */}
        <circle cx="100" cy="40" r="5" fill="var(--primary)" opacity="0.6" />
        <circle cx="160" cy="75" r="4" fill="var(--accent)" opacity="0.7" />
        <circle cx="155" cy="145" r="5" fill="var(--primary)" opacity="0.5" />
        <circle cx="55" cy="155" r="4" fill="var(--accent)" opacity="0.6" />
        <circle cx="35" cy="80" r="5" fill="var(--primary)" opacity="0.6" />
        <circle cx="145" cy="110" r="3" fill="var(--accent)" opacity="0.5" />

        {/* Connection lines */}
        <line x1="100" y1="100" x2="100" y2="40" stroke="var(--primary)" strokeWidth="0.8" opacity="0.25" />
        <line x1="100" y1="100" x2="160" y2="75" stroke="var(--primary)" strokeWidth="0.8" opacity="0.25" />
        <line x1="100" y1="100" x2="155" y2="145" stroke="var(--primary)" strokeWidth="0.8" opacity="0.25" />
        <line x1="100" y1="100" x2="55" y2="155" stroke="var(--primary)" strokeWidth="0.8" opacity="0.25" />
        <line x1="100" y1="100" x2="35" y2="80" stroke="var(--primary)" strokeWidth="0.8" opacity="0.25" />
        <line x1="100" y1="100" x2="145" y2="110" stroke="var(--primary)" strokeWidth="0.8" opacity="0.2" />
      </svg>
    </div>
  );
}
