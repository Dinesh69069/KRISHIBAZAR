'use client';

import { useEffect, useState } from 'react';

type Item = { id: string; label: string };

/** Sticky "On this page" index with scroll-spy highlighting. */
export default function SideIndex({ items }: { items: Item[] }) {
  const [active, setActive] = useState(items[0]?.id);

  useEffect(() => {
    const spy = () => {
      const y = window.scrollY + 140;
      let current = items[0]?.id;
      for (const item of items) {
        const el = document.getElementById(item.id);
        if (el && el.offsetTop <= y) current = item.id;
      }
      setActive(current);
    };
    spy();
    window.addEventListener('scroll', spy, { passive: true });
    return () => window.removeEventListener('scroll', spy);
  }, [items]);

  const go = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.getElementById(id)?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  };

  return (
    <aside className="side" aria-label="On this page">
      <p>On this page</p>
      {items.map((item) => (
        <a
          key={item.id}
          href={`#${item.id}`}
          className={active === item.id ? 'act' : undefined}
          onClick={(e) => go(e, item.id)}
        >
          {item.label}
        </a>
      ))}
    </aside>
  );
}
