"use client";
import { useState } from "react";

const PLANS = [
  {
    code: "pro_monthly",
    label: "30 дней",
    price: "299 ₽",
    per: "в месяц",
    popular: true,
  },
  {
    code: "pro_yearly",
    label: "365 дней",
    price: "1 990 ₽",
    per: "в год (экономия 66%)",
    popular: false,
  },
];

const FREE_FEATURES = ["Канал с вирусными роликами", "Обновления каждый день", "Shorts и Reels"];
const PRO_FEATURES = [...FREE_FEATURES, "🔥 PRO-канал — самое отборное", "⚡ Ранний доступ за 12 часов", "📂 Тематические подборки", "🚫 Без рекламы"];

type Provider = "yookassa" | "prodamus";

export function Pricing() {
  const [loading, setLoading] = useState(false);
  const [tgId, setTgId] = useState("");
  const [email, setEmail] = useState("");
  const [provider, setProvider] = useState<Provider>("yookassa");
  const [error, setError] = useState("");

  async function handleBuy(code: string) {
    if (!tgId) { setError("Введи Telegram ID"); return; }
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_PAYMENTS_URL ?? "/api"}/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, product_code: code, tg_id: Number(tgId), email }),
      });
      const data = await res.json();
      if (data.confirmation_url) {
        window.location.href = data.confirmation_url;
      } else {
        setError("Ошибка при создании платежа");
      }
    } catch {
      setError("Ошибка соединения с платёжным сервисом");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="pricing" style={{ maxWidth: 820, margin: "0 auto", padding: "0 24px 100px" }}>
      <h2 style={{ textAlign: "center", fontSize: "1.8rem", fontWeight: 700, marginBottom: 12 }}>Тарифы</h2>
      <p style={{ textAlign: "center", color: "#888", marginBottom: 48 }}>Бесплатный канал открыт для всех. PRO добавляет отборное.</p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 20, marginBottom: 40 }}>
        {/* Free */}
        <div style={{ background: "#141414", border: "1px solid #222", borderRadius: 12, padding: 28 }}>
          <div style={{ fontWeight: 700, fontSize: "1.1rem", marginBottom: 4 }}>Бесплатно</div>
          <div style={{ fontSize: "2rem", fontWeight: 800, marginBottom: 20 }}>0 ₽</div>
          <ul style={{ listStyle: "none", color: "#bbb", display: "flex", flexDirection: "column", gap: 10 }}>
            {FREE_FEATURES.map(f => <li key={f}>✓ {f}</li>)}
          </ul>
          <a
            href={process.env.NEXT_PUBLIC_TG_BOT_URL ?? "#"}
            style={{ display: "block", marginTop: 24, padding: "12px 0", textAlign: "center", border: "1px solid #333", borderRadius: 8, color: "#ccc", fontWeight: 600 }}
          >
            Подписаться
          </a>
        </div>

        {/* PRO */}
        <div style={{ background: "#1a0e08", border: "1px solid #ff4d00", borderRadius: 12, padding: 28 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: "1.1rem" }}>PRO</span>
            <span style={{ background: "#ff4d00", color: "#fff", borderRadius: 999, padding: "2px 10px", fontSize: 12, fontWeight: 700 }}>ХИТ</span>
          </div>
          <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
            {PLANS.map(p => (
              <div key={p.code} style={{ flex: 1, border: "1px solid #333", borderRadius: 8, padding: "10px 12px", cursor: "pointer", textAlign: "center" }}>
                <div style={{ fontWeight: 700 }}>{p.price}</div>
                <div style={{ fontSize: 11, color: "#888" }}>{p.per}</div>
              </div>
            ))}
          </div>
          <ul style={{ listStyle: "none", color: "#ccc", display: "flex", flexDirection: "column", gap: 10, marginBottom: 24 }}>
            {PRO_FEATURES.map(f => <li key={f}>{f}</li>)}
          </ul>

          {/* Checkout form */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <input
              type="text"
              placeholder="Твой Telegram ID (числовой)"
              value={tgId}
              onChange={e => setTgId(e.target.value)}
              style={{ background: "#0a0a0a", border: "1px solid #333", borderRadius: 8, padding: "10px 12px", color: "#fff", fontSize: 14, outline: "none" }}
            />
            <input
              type="email"
              placeholder="Email (для чека, необязательно)"
              value={email}
              onChange={e => setEmail(e.target.value)}
              style={{ background: "#0a0a0a", border: "1px solid #333", borderRadius: 8, padding: "10px 12px", color: "#fff", fontSize: 14, outline: "none" }}
            />
            <select
              value={provider}
              onChange={e => setProvider(e.target.value as Provider)}
              style={{ background: "#0a0a0a", border: "1px solid #333", borderRadius: 8, padding: "10px 12px", color: "#ccc", fontSize: 14, outline: "none" }}
            >
              <option value="yookassa">ЮKassa (карты РФ)</option>
              <option value="prodamus">Prodamus</option>
            </select>
            {error && <div style={{ color: "#ff6b6b", fontSize: 13 }}>{error}</div>}
            <button
              onClick={() => handleBuy("pro_monthly")}
              disabled={loading}
              style={{ background: "#ff4d00", color: "#fff", border: "none", borderRadius: 8, padding: "14px 0", fontWeight: 700, fontSize: "1rem", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}
            >
              {loading ? "Переходим к оплате..." : "Оформить PRO за 299 ₽/мес"}
            </button>
          </div>
        </div>
      </div>
      <p style={{ textAlign: "center", color: "#555", fontSize: 13 }}>
        Оплата через ЮKassa или Prodamus. Отмена в любой момент.
      </p>
    </section>
  );
}
