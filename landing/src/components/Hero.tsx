import Link from "next/link";

const TG_URL = process.env.NEXT_PUBLIC_TG_BOT_URL ?? "#";

export function Hero() {
  return (
    <section style={{
      maxWidth: 760,
      margin: "0 auto",
      padding: "96px 24px 64px",
      textAlign: "center",
    }}>
      <div style={{ display: "inline-block", background: "#ff4d0020", color: "#ff4d00", borderRadius: 999, padding: "4px 14px", fontSize: 13, fontWeight: 600, marginBottom: 24 }}>
        🔥 Обновляется каждый день
      </div>
      <h1 style={{ fontSize: "clamp(2.2rem, 6vw, 3.6rem)", fontWeight: 800, lineHeight: 1.1, marginBottom: 20 }}>
        Самые вирусные ролики —<br />
        <span style={{ color: "#ff4d00" }}>уже в твоём телефоне</span>
      </h1>
      <p style={{ fontSize: "1.15rem", color: "#aaa", maxWidth: 520, margin: "0 auto 40px" }}>
        Мы просматриваем тысячи роликов в день. Claude AI отбирает только то,
        что реально цепляет. Ты получаешь лучшее — без мусора.
      </p>
      <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
        <a
          href={TG_URL}
          style={{
            background: "#ff4d00",
            color: "#fff",
            padding: "14px 28px",
            borderRadius: 10,
            fontWeight: 700,
            fontSize: "1rem",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          📲 Подписаться бесплатно
        </a>
        <Link
          href="#pricing"
          style={{
            border: "1px solid #333",
            color: "#ccc",
            padding: "14px 28px",
            borderRadius: 10,
            fontWeight: 600,
            fontSize: "1rem",
          }}
        >
          PRO-доступ →
        </Link>
      </div>
    </section>
  );
}
