const TG_URL = process.env.NEXT_PUBLIC_TG_BOT_URL ?? "#";

export function Footer() {
  return (
    <footer style={{ borderTop: "1px solid #1a1a1a", padding: "32px 24px", textAlign: "center", color: "#444", fontSize: 13 }}>
      <div style={{ marginBottom: 12 }}>
        <a href={TG_URL} style={{ color: "#666", marginRight: 20 }}>Telegram-бот</a>
        <a href="#pricing" style={{ color: "#666", marginRight: 20 }}>Тарифы</a>
        <a href="/privacy" style={{ color: "#666" }}>Политика конфиденциальности</a>
      </div>
      <div>© {new Date().getFullYear()} YAg. Все права защищены.</div>
    </footer>
  );
}
