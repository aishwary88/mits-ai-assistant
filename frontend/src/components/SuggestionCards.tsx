import {
  GraduationCap,
  Users,
  Wallet,
  Briefcase,
  CalendarDays,
  Building2,
  type LucideIcon,
} from 'lucide-react';

interface Card {
  icon: LucideIcon;
  category: string;
  question: string;
}

const CARDS: Card[] = [
  { icon: GraduationCap, category: 'Academics', question: 'When are the Mid-Sem exams?' },
  { icon: Users, category: 'Faculty', question: 'Find CSD faculty members' },
  { icon: Wallet, category: 'Fees', question: 'Show B.Tech fee structure' },
  { icon: Briefcase, category: 'Placements', question: 'Tell me about placements' },
  { icon: CalendarDays, category: 'Calendar', question: 'Show the academic calendar' },
  { icon: Building2, category: 'Campus', question: 'What facilities does MITS have?' },
];

interface Props {
  onCardClick: (question: string) => void;
}

export function SuggestionCards({ onCardClick }: Props) {
  return (
    <div className="w-full">
      <div className="mb-3 text-[0.7rem] font-semibold uppercase tracking-wider text-text-muted">
        Explore MITS
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <button
              key={card.category}
              onClick={() => onCardClick(card.question)}
              className="group rounded-lg border border-border bg-surface p-4 text-left transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus-visible:-translate-y-0.5"
            >
              <div className="mb-2 flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-light text-primary transition-colors group-hover:bg-primary group-hover:text-white">
                  <Icon className="h-4 w-4" />
                </span>
                <span className="text-[0.7rem] font-bold uppercase tracking-wider text-primary">
                  {card.category}
                </span>
              </div>
              <p className="text-sm text-text-muted transition-colors group-hover:text-text">
                {card.question}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
