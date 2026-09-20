'use client';

type Tab = 'mandis' | 'forecast';

type ResultsTabsProps = {
  activeTab: Tab;
  onChange: (tab: Tab) => void;
};

const tabs: { id: Tab; label: string }[] = [
  { id: 'mandis', label: 'Recommended mandis' },
  { id: 'forecast', label: '7-day price' },
];

export default function ResultsTabs({ activeTab, onChange }: ResultsTabsProps) {
  const move = (currentIndex: number, direction: 'next' | 'previous' | 'first' | 'last') => {
    const nextIndex = direction === 'next'
      ? (currentIndex + 1) % tabs.length
      : direction === 'previous'
        ? (currentIndex - 1 + tabs.length) % tabs.length
        : direction === 'first'
          ? 0
          : tabs.length - 1;
    onChange(tabs[nextIndex].id);
    document.getElementById(`results-tab-${tabs[nextIndex].id}`)?.focus();
  };

  return (
    <div className="results-tabs" role="tablist" aria-label="Rate card results">
      {tabs.map((tab, index) => (
        <button
          key={tab.id}
          id={`results-tab-${tab.id}`}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-controls={`results-panel-${tab.id}`}
          tabIndex={activeTab === tab.id ? 0 : -1}
          className={`results-tab${activeTab === tab.id ? ' active' : ''}`}
          onClick={() => onChange(tab.id)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowRight') move(index, 'next');
            if (event.key === 'ArrowLeft') move(index, 'previous');
            if (event.key === 'Home') move(index, 'first');
            if (event.key === 'End') move(index, 'last');
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
