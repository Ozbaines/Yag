const items = [
  { icon: "🤖", title: "AI-фильтрация", desc: "Claude оценивает каждый ролик по 5 критериям вирусности. Проходит только топ." },
  { icon: "✂️", title: "Нарезка под Shorts", desc: "Длинные видео автоматически режутся на вертикальные клипы 9:16 с Whisper-субтитрами." },
  { icon: "⚡️", title: "Ежедневные обновления", desc: "Контент обновляется каждые 15 минут из YouTube, Reddit и других источников." },
  { icon: "🌍", title: "Мировые тренды", desc: "Собираем вирусное с RU и EN интернета. Подаём на русском языке." },
  { icon: "📺", title: "Reels + Shorts", desc: "Каждый пост автоматически уходит в Instagram Reels и YouTube Shorts." },
  { icon: "💎", title: "PRO-канал", desc: "Подписчики PRO получают самое отборное на 12 часов раньше всех." },
];

export function Features() {
  return (
    <section style={{ maxWidth: 900, margin: "0 auto", padding: "0 24px 80px" }}>
      <h2 style={{ textAlign: "center", fontSize: "1.8rem", fontWeight: 700, marginBottom: 48 }}>
        Как это работает
      </h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20 }}>
        {items.map((it) => (
          <div
            key={it.title}
            style={{ background: "#141414", border: "1px solid #222", borderRadius: 12, padding: "24px 20px" }}
          >
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>{it.icon}</div>
            <h3 style={{ fontWeight: 700, marginBottom: 8 }}>{it.title}</h3>
            <p style={{ color: "#888", fontSize: "0.9rem", lineHeight: 1.6 }}>{it.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
